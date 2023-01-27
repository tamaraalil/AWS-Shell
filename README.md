# aws-shell
A shell for an AWS user to access and manipulate their S3 objects.

## Compile and Run
- Fill out "S5-S3.conf" file with your AWS key id and secret key ID
- python3 shell.py

## Notes
- This program assumes that paths starting with '/' are full paths (bucket name at the beginning), and paths without a slash at the beginning are relative paths.

## Commands 
Local Commands
- This shell passes all bash/zsh commands on your local computer.

###locs3cp
- Uploads a file from local system to cloud
- Usage: 
```locs3cp <full or relative pathname of local file> /<bucket name>/<full pathname of S3>```

###s3loccp
- Downloads a file from the cloud to your local system
- Usage:
```s3loccp /<bucket name>/<full pathname of S3 file> <full/relative pathname of the local file>```

###create_bucket
- Creates a bucket in the cloud
- Usage:
```create_bucket /<bucket name>```

###create_folder
- Creates a folder in the cloud
- Usage:
```create_folder <full or relative pathname for the folder>```

###chlocn 
- Change directory in S3 storage buckets/folders, like "cd"
- Supports "chlocn ..", "chlocn ../..", and "chlocn"
- Usage:
```chlocn <full or relative pathname of directory>```

###cwlocn
- Prints current working directory
- Usage:
```cwd```

###list
- Lists objects/buckets in a directory, like "ls"
- Adding -l flag lists more information about the objects
- Usage:
```list```
```list -l```       
```list <full or relative pathname of directory>```

###s3copy
- Copies an S3 object from one location to another
- Usage:
```s3copy <from S3 location of object> <to S3 location>```

###delete_bucket
- Deletes a bucket in S3 storage
- Usage:
```delete_bucket <bucket name>```

###s3delete
- Deletes an object in S3 storage
- Usage:
```s3delete <full or relative pathname of object>```
