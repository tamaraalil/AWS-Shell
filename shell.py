import configparser
import os 
import sys 
import pathlib
import boto3
import shlex
import subprocess

# Program Name: shell.py
# Author: Tamara Alilovic

# -------------------- GLOBAL VARIABLES --------------------

currBucket = ""
pwd = ""

# -------------------- HELPER FUNCTIONS --------------------

# Create connection to AWS
def connectAWS():
    # Parse id & key from config file
    config = configparser.ConfigParser()
    config.read("S5-S3.conf")
    aws_access_key_id = config['default']['aws_access_key_id']
    aws_secret_access_key = config['default']['aws_secret_access_key']
    try:
        # Establish an AWS session
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        # Set up client and resources
        s3 = session.client('s3')
        s3_res = session.resource('s3')

        print("You are now connected to your S3 storage")

    except: # Error messsage if connection does not work
        print("You could not be connected to your S3 storage")
        print("Please review procedures for authenticating your account on AWS S3")
    
    return s3, s3_res


# Parse full directory paths
def parseFullPath(s3, inp):
    bucketInfo = list(filter(None, inp.split("/", 2)))
    bucket = bucketInfo[0]
    temp = ""
    for i in range(1, len(bucketInfo)):
        temp = temp + '/' + bucketInfo[i]
    path = temp[1:]
    validateBucket(s3, bucket)# Stop if bucket does not exist
    return bucket, path


# Parse relative directory paths
def parseRelativePath(s3, inp, valid):
    global currBucket
    global pwd

    if currBucket == "": # Give error if relative path was given while in root dir
        print("Object does not exist.")
        return 1
    bucket = currBucket
    # Parse path & add it to current path
    directory = []
    if '/' in inp:
        directory = list(filter(None, inp.split("/")))
    else: 
        directory.append(inp)
    temp = ""
    for i in range(0, len(directory)):
        temp = temp + '/' + directory[i]
    path = temp[1:]
    path = pwd + path
    if valid == 1:
        validateObject(s3, bucket, path) # Stop if the object doesn't exist

    return bucket, path


# Validate if a bucket exists
def validateBucket(s3, bucket):
    try:
        s3.head_bucket(Bucket = bucket) 
    except:
        print("Bucket does not exist.")


# Validate if an object exists
def validateObject(s3, bucket, path):
    # Get list of objects in given bucket
    objects = []
    response = s3.list_objects(Bucket = bucket)
    for obj in response['Contents']:
        objects.append(obj["Key"])
    # Check if object (path) exists in bucket
    res = any(path in word for word in objects)
    if (('/'+path) in objects) or (path in objects) or res:
        return True
    else:
        print("Object (folder(s) or file) does not exist.")
        return False

# List buckets
def listBuckets(s3, longFlag):
    # Get list of buckets
    buckets = []
    date = []
    response = s3.list_buckets()
    for bucket in response['Buckets']:
        buckets.append(bucket["Name"])
        if longFlag == 1: # Get extra info for -l tag
            date.append(bucket['CreationDate'])
    i = 0
    for bucket in buckets:
        if longFlag == 1:
            print(f'{date[i]}\t{bucket}')
        else:
            print (bucket)
        i = i + 1

# -------------------- COMMAND FUNCTIONS --------------------

# Upload file from local system to cloud - locs3cp
def upload(s3, args):
    # Error check input
    if len(args) != 3:
        print("Cannot perform upload - invalid arguments.")
        print("Usage: locs3cp <full or relative pathname of local file> /<bucket name>/<full pathname of S3>")
        return 1
    if args[2] == '/':
        print("Cannot upload file to root directory.")
        return 1

    # Parse argument input
    if args[2][0] == '/':
        bucketInfo = list(filter(None, args[2].split("/", 2)))
    else:
        bucketInfo = list(filter(None, args[2].split("/", 1)))
    try:
        s3.upload_file(args[1], bucketInfo[0], bucketInfo[1])
    except: # Error message
        print("Upload file unsuccessful.")
        return 1
    return 0


# Download file from cloud to local system - s3loccp
def download(s3, args):
    if len(args) != 3: # Error check input
        print("Cannot perform download - invalid arguments.")
        print("Usage: s3loccp /<bucket name>/<full pathname of S3 file> <full/relative pathname of the local file>")
        return 1

    bucketName = ""
    path = ""

    # Parse first argument for bucket name & cloud filename
    if args[1][0] == '/':
        bucketName, path = parseFullPath(s3, args[1])
    else:
        bucketName, path = parseRelativePath(s3, args[1], 1)

    # Download object
    try:
        s3.download_file(bucketName, path, args[2])
    except: # Error message
        print("Download file unsuccessful.")
        return 1
    return 0


# Create a bucket - create_bucket
def createBucket(s3, args):
    if len(args) != 2: # Error check arguments
        print("Cannot create bucket - invalid arguments.")
        print("Usage: create_bucket /<bucket name>")
        return 1

    try:
        bucketName = args[1].replace('/', '') # Parse bucket name   
        s3.create_bucket(
            Bucket=bucketName,
            CreateBucketConfiguration={
                'LocationConstraint': 'ca-central-1',
            },
        )
    except: # Error message
        print("Cannot create bucket - try a different bucket name.")
        return 1
    return 0
    

# Create a folder - create_folder
def createFolder(s3, args):
    if len(args) != 2: # Error check input
        print("Cannot create folder - invalid arguments.")
        print("Usage: create_folder <full or relative pathname for the folder>")
        return 1

    if args[1][0] == '/': # Full path given
        bucketName, directory = parseFullPath(s3, args[1])
    else: # Relative path given
        bucketName, directory = parseRelativePath(s3, args[1], 0)

    try:
        s3.put_object(Bucket = bucketName, Key = directory+'/')
    except:
        print("Cannot create folder.")
        return 1
    return 0


# Change directory - chlocn
def changeDir(s3, args):
    if len(args) > 2: # Error check input
        print("Cannot change folder - invalid arguments.")
        print("Usage: chlocn <full or relative pathname of directory>")
        return 1

    global currBucket
    global pwd
    directory = ""

    # Return to beginning directory
    if len(args) == 1 or args[1] == '~' or args[1] == '/':
        currBucket = ""
        pwd = ""
        return 0

    # Go back two folders if ../.. is typed
    if args[1] == '../..':
        path = list(filter(None, pwd.split("/")))
        pwd = ""
        # If there is nowhere to ../.. into, go to root directory
        if (len(path) - 2) < 0:
            currBucket = ""
            pwd = ""
        elif (len(path) - 2) >= 2: # Create new pwd without last two folders
            for i in range(0, len(path) - 2):
                pwd = pwd + '/' + path[i]
            if pwd == "": # If now in root dir, reset current bucket
                currBucket == ""
        return 0

    # Removing a folder when .. is present
    if '..' in args[1]:
        path = list(filter(None, pwd.split("/")))
        pwd = ""
        # If there is nowhere to .. into, go to root directory
        if len(path) - 1 < 0:
            currBucket = ""
            pwd = ""
            return 1
        elif len(path) - 1 >= 1: # Create new pwd without last folder
            for i in range(0, len(path) - 1):
                pwd = pwd + path[i] + '/'
            if pwd == "": # If now in root dir, reset current bucket
                currBucket == ""
        if "/" in args[1]:
            path = list(filter(None, args[1].split("/")))
            for i in range(1, len(path)):
                directory = directory + path[i] + '/'
            pwd = pwd + directory
        return 0

    if args[1][0] == '/': # Full path given - get bucket name
        bucketName, directory = parseFullPath(s3, args[1])
    else: # Relative path given
        if pwd == "":
            bucketName, directory = parseFullPath(s3, '/'+currBucket+'/'+args[1])
        else:
            bucketName, directory = parseFullPath(s3, '/'+currBucket+'/'+pwd+'/'+args[1])
        validateObject(s3, bucketName, directory) # Stop if the folder(s) don't exist

    # Save bucket and path as current location using global variables
    currBucket = bucketName
    pwd = directory
    return 0
    

# Print current working directory - cwlocn
def cwd():
    if currBucket == "": # Root directory
        print("/")
    else:
        print(f"/{currBucket}/{pwd}")
    return 0


# List objects/buckets in a directory - list
def printList(s3, s3_res, args):
    if len(args) > 3: # Error check input
        print("Cannot list contents of this S3 location - invalid arguments.")
        print("Usage: list\n       list-l\n       list <full or relative pathname of directory>")
        return 1

    path = ""
    bucketName = ""
    longFlag = 0
    # Parse input
    if len(args) == 1: # Input is just "list"
        if currBucket != "": # If in a bucket, get current bucket & current path
            bucketName = currBucket
            if pwd == "":
                path = pwd
            else:
                path = pwd + '/'
        else: # If not in a bucket already, list buckets
            listBuckets(s3, 0)
            return 0
    elif len(args) == 2: # Input is "list <path>" or "list -l"
        if args[1] == '-l':
            if currBucket == "": # If in root directory, print buckets w/ long info
                listBuckets(s3, 1)
                return 0
            else: # In bucket
                longFlag = 1
                path = pwd 
                if path != "":
                    path = path + '/'
        if args[1] == '/': # Print root directory (buckets)
            listBuckets(s3, 0)
            return 0
        elif args[1][0] == '/': # Full path given
            bucketName, path = parseFullPath(s3, args[1])
            if path != "":
                path = path + '/'
        else: # Relative path
            if currBucket == "": # Give error if relative path was given while in root dir
                print("Folder does not exist.")
                return 1
            bucketName = currBucket
            if args[1] == '-l':
                longFlag = 1
                if pwd == "":
                    path = pwd
                else: # Add / at the end if already in a folder
                    path = pwd + '/'
            else:
                if pwd == "":
                    bucketName, path = parseFullPath(s3, '/'+currBucket+'/'+args[1])
                else:
                    bucketName, path = parseFullPath(s3, '/'+currBucket+'/'+pwd+'/'+args[1])
                validateObject(s3, bucketName, path) # Stop if the folder(s) don't exist
                path = path + '/'
    elif len(args) == 3: # Input is "list -l <path>"
        if args[1] == '-l':
            longFlag = 1
            if args[2][0] == '/': # Full path given
                bucketName, path = parseFullPath(s3, args[2])
                if path != "":
                    path = path + '/'
            else: # Relative path given
                bucketName, path = parseRelativePath(s3, args[2], 1)
                path = path + '/'
        else:
            print("Input for this command is incorrect.")
            return 1

    # Print results
    if pwd == "" and path == "": # In a bucket
        # Get list of objects in bucket
        objects = []
        sizes = []
        storage = []
        date = []
        response = s3.list_objects(Bucket = bucketName)
        for obj in response['Contents']:
            objects.append(obj["Key"])
            if longFlag == 1: # Get extra info for -l tag
                sizes.append(obj["Size"])
                storage.append(obj["StorageClass"])
                date.append(obj["LastModified"])
        # Only print top-level files/folders in bucket
        i = 0
        for obj in objects:
            if longFlag == 1:
                if obj.count('/') <= 1: # -l print
                    print(f'{storage[i]}\t{sizes[i]}\t{date[i]}\t{obj}')
            else:
                if obj.count('/') <= 1:
                    print(obj)
            i = i + 1
    else: # In a folder
        # Print folders in folder
        result = s3.list_objects(Bucket=bucketName, Prefix=path, Delimiter='/')
        if result.get('CommonPrefixes') != None:
            for obj in result.get('CommonPrefixes'):
                print(obj.get('Prefix').replace(path, ''))
        # Print files in folder
        my_bucket = s3_res.Bucket(bucketName)
        for objects in my_bucket.objects.filter(Prefix=(path), Delimiter='/'):
            if objects.key != path:
                print((objects.key).replace(path, ''))

    return 0
    

# Delete a bucket - delete_bucket
def deleteBucket(s3, args):
    if len(args) != 2: # Error check arguments
        print("Cannot delete bucket - invalid arguments.")
        print("Usage: delete_bucket <bucket name>")
        return 1

    bucketName = args[1].replace('/', '')
    if bucketName == currBucket: # Check if user is in to-delete bucket
        print("Cannot delete the bucket you are currently in.")
        return 1
    else:
        validateBucket(s3, bucketName) # Stop if bucket does not exist
        try:
            s3.delete_bucket(Bucket = bucketName)
        except:
            print("Cannot delete bucket")
            return 1
    return 0


# Delete an object - s3delete
def deleteObject(s3, s3_res, args):
    if len(args) != 2: # Error check arguments
        print("Cannot delete object - invalid arguments.")
        print("Usage: s3delete <full or relative pathname of object>")
        return 1
    
    path = ""
    bucketName = ""
    if args[1][0] == '/': # Full path given
        bucketName, path = parseFullPath(s3, args[1])
    else: # Relative path given
        bucketName, path = parseRelativePath(s3, args[1], 1)

    if path == "": # In bucket
        # Get list of objects in bucket
        objects = []
        response = s3.list_objects(Bucket = bucketName)
        for obj in response['Contents']:
            objects.append(obj["Key"])
        done = 0
        # Delete object
        for obj in objects:
            if path+'/' == obj: # Delete folder
                s3.delete_object(Bucket = bucketName, Key = path+'/')
                done = 1
            elif path == obj: # Delete file
                s3.delete_object(Bucket = bucketName, Key = path)
                done = 1
        if done == 0: # Error message
            print("Cannot perform delete")
            return 1
    else: # In folder
        # Get list of objects in folder
        my_bucket = s3_res.Bucket(bucketName)
        done = 0
        for objects in my_bucket.objects.filter(Prefix=path):
            if (path+'/') == objects.key: # Delete folder
                s3.delete_object(Bucket = bucketName, Key = path+'/')
                done = 1
            elif path == objects.key: # Delete file
                s3.delete_object(Bucket = bucketName, Key = path)
                done = 1
        if done == 0: # Error message
            print("Cannot perform delete")
            return 1
    return 0


# Copy object from one bucket to another - s3copy
def copyObject(s3, args):
    if len(args) != 3: # Error check input
        print("Cannot perform copy - invalid arguments.")
        print("Usage: s3copy <from S3 location of object> <to S3 location>")
        return 1
    
    fromBucket = ""
    fromPath = ""
    destBucket = ""
    destPath = ""

    # Parse input
    if args[1][0] == '/': # Full path given
        fromBucket, fromPath = parseFullPath(s3, args[1])
    else: # Relative path given
        fromBucket, fromPath = parseRelativePath(s3, args[1], 1)

    if args[2][0] == '/': # Full path given
        destBucket, destPath = parseFullPath(s3, args[2])
    else: # Relative path given
        destBucket, destPath = parseRelativePath(s3, args[2], 1)
    
    # Parse input for source path
    source = fromBucket + '/' + fromPath
    # Parse input for destination key
    temp = list(filter(None, fromPath.split("/")))
    filename = temp[len(temp) - 1]
    destPath = destPath + '/' + filename

    try:
        s3.copy_object(Bucket = destBucket, CopySource = source, Key = destPath)
    except:
        print("Cannot perform copy.")
        return 1
    return 0

# ---------------------- MAIN FUNCTION ----------------------

def main():
    global currBucket
    global pwd

    print ("Welcome to the AWS S3 Storage Shell (S5)")
    s3, s3_res = connectAWS()

    while True:
        inp = input('S5> ') # Get input from user
        if 'exit' == inp.rstrip() or 'quit' == inp.rstrip(): # Exit command
            print("Exiting")
            exit()
        else:
            try:
                args = shlex.split(inp)
                if 'locs3cp' == args[0]:
                    upload(s3, args)
                elif 's3loccp' == args[0]:
                    download(s3, args)
                elif 'create_bucket' == args[0]:
                    createBucket(s3, args)
                elif 'create_folder' == args[0]:
                    createFolder(s3, args)
                elif 'chlocn' == args[0]:
                    changeDir(s3, args)
                elif 'cwlocn' == args[0]:
                    cwd()
                elif 'list' == args[0]:
                    printList(s3, s3_res, args)
                elif 'delete_bucket' == args[0]:
                    deleteBucket(s3, args)
                elif 's3delete' == args[0]:
                    deleteObject(s3, s3_res, args)
                elif 's3copy' == args[0]:
                    copyObject(s3, args)
                else:
                    subprocess.run(shlex.split(inp))
            except:
                print("command not found: ", inp)

if __name__ == "__main__":
    main()
