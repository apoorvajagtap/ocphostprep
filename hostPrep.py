import os
import paramiko
import getpass
from multiprocessing import Process, Manager
import yaml

rhnId = input("\nEnter RHN Customer Id: ")
rhnPassword = getpass.getpass(prompt="\nEnter RHN Password: ")
version = False
while not version:
    ocpVersion = input("\nEnter OpenShift Version (3.9 | 3.10 | 3.11): ")
    if ocpVersion in ('3.9', '3.10', '3.11'):
        version = True
    else:
        version = False

userPassword = getpass.getpass(prompt="\nEnter root password for nodes: ")
ipFile = input("\nEnter file name with list of ip: ")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
failedIpList = Manager().dict()
pList = []
cmdList = []
if os.path.exists("./logFiles"):
    os.system("rm -rf ./logFiles")
os.mkdir("./logFiles")


def errStatus(ip, stdout, stderr, failedIpList, step):
    output = ""
    output = output.join(stdout.readlines())
    os.system("echo '{}' >> ./logFiles/{}".format(output, ip))
    error = stderr.readlines()
    if error:
        print(ip, " [ERROR]: ", step)
        failedIpList.update({ip: step})
        exit(1)
    else:
        print(ip, " >>", step, "COMPLETED SUCCESSFULLY!!")


def executeCommand(ip, failedIpList):
    try:
        ssh.connect(ip, port=22, username='root', password=userPassword, timeout=5)
    except:
        print("\nCONNECTION CANNOT BE ESTABLISHED: SKIPPING ", ip)
        failedIpList.update({ip: "CONNECTION-ERROR"})
        return

    stdin, stdout, stderr = ssh.exec_command(
        "subscription-manager register --username={} --password={} --force".format(rhnId, rhnPassword))
    errStatus(ip, stdout, stderr, failedIpList, "REGISTRATION")

    with open("yaml_file.yaml", 'r') as yaml_file:
        yaml_reader = yaml.load(yaml_file, Loader=yaml.FullLoader)
        for items, value in yaml_reader.items():
            if ocpVersion == items:
                cmdList = value
    yaml_file.close()
    for line in cmdList:
        step, cmd = line.split(':')
        stdin, stdout, stderr = ssh.exec_command(cmd)
        # print(stdout.readlines())
        errStatus(ip, stdout, stderr, failedIpList, step)


def checkthreading():
    try:
        fp = open(ipFile, 'r')

    except:
        print("FILE NOT FOUND")
        exit(1)

    for ip in fp.readlines():
        # os.system("touch ./logFiles/{}".format(ip))
        p = Process(target=executeCommand, args=(ip, failedIpList,))
        p.start()
        pList.append(p)

    for temp in pList:
        temp.join()


if __name__ == '__main__':
    checkthreading()
    print("\nFAILED CONNECTIONS: ", failedIpList)