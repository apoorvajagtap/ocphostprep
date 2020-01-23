import os
import paramiko
import getpass
from multiprocessing import Process,Manager
import yaml

# Taking Input
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

# Defining empty lists and dictionary
failedIpDict = Manager().dict()
pList = []
cmdList = []

# Establishing SSH connection
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# If logFile directory already exists, remove and create it
if os.path.exists("./logFiles"):
    os.system("rm -rf ./logFiles")
os.mkdir("./logFiles")

# Checks for any errors, and provides output accordingly
def errStatus(ip, stdout, stderr, failedIpDict, step):
    output = ""
    output = output.join(stdout.readlines())
    os.system("echo '{}' >> ./logFiles/{}".format(output, ip))
    error = stderr.readlines()
    if error:
        print(ip, " [ERROR]: ", error, "-> at : ", step)
        failedIpDict.update({ip : step})
        exit(1)
    else:
        print(ip, " >>", step, "COMPLETED SUCCESSFULLY!!")
        
# Command execution over nodes
def executeCommand(ip, failedIpDict):
    try:
        ssh.connect(ip, port=22, username='root', password=userPassword, timeout=5)
    except:
        print("\nCONNECTION CANNOT BE ESTABLISHED: SKIPPING ", ip)
        failedIpDict.update({ip : "CONNECTION-ERROR"})
        return
    
    # Executing subscription registration command over nodes
    stdin, stdout, stderr = ssh.exec_command("subscription-manager register --username={} --password={} --force".format(rhnId, rhnPassword))
    errStatus(ip, stdout, stderr, failedIpDict, "REGISTRATION")
    
    # Reading version specific commands from yaml file and appending them into cmdList list
    with open("versionFile.yaml",'r') as yaml_file:
        yaml_reader = yaml.load(yaml_file, Loader=yaml.FullLoader)
        for items,value in yaml_reader.items():
            if ocpVersion == items:
                cmdList = value
    yaml_file.close()

    # Reading commands from cmdList list and executing them
    for line in cmdList:
        step, cmd = line.split(':')
        stdin, stdout, stderr = ssh.exec_command(cmd)
        errStatus(ip, stdout, stderr, failedIpDict, step)

# Multiprocessing implemented
def checkthreading():
    try:
        fp = open(ipFile, 'r')
    except:
        print("FILE NOT FOUND")
        exit(1)
    if (os.stat(ipFile).st_size != 0):
        for ip in fp.readlines():
            p = Process(target=executeCommand, args=(ip, failedIpDict, ))
            p.start()
            pList.append(p)
    
        for temp in pList: 
            temp.join()
    else:
        print("\nFile is empty!!\n")

# Main method
if __name__ == '__main__':
    checkthreading() 
    if failedIpDict:
        print("\nFAILED CONNECTIONS: \n", failedIpDict) 
    else:
        print("\n COMPLETED!! \n")
