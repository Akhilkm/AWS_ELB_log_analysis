##########################################################################################
#                         Python script to parse elb logs and find                       #
#				urls causing 4xx/5xx errrors                             #  
##########################################################################################


import boto3
import time
import os
import re
import calendar



########################################################################
#  Steps to download logs from s3 and return the logs as list          #
########################################################################



#function to select customer and returns cross account arn associates with client
def select_client(client):
	values = client.scan(TableName='AWS-ServiceLimit-Checker')['Items']
	print "\t\tSelect Customer\n*********************************************"
	i = 1
	for value in values:
		print str(i) + ". " + str(value['client']['S'])
		i += 1
	no = int(raw_input("Enter client Number: "))
	try:
		reply = raw_input( "You have selected " + str(values[no-1]['client']['S']) + ", do you want to continue(Y/N): ")
	except:
		print "Invalid Option"
		exit()
	if reply == 'y' or reply =='Y':
		return str(values[no-1]['crossaccountarn']['S'])
	else:
		exit()
#function to select region
def get_region(client):
	regions = client.describe_regions()['Regions']
	print "\t\tSelect Region\n***********************************************"
	i = 1
	values = []
	for region in regions:
		print str(i) + ". " + region['RegionName']
		i += 1
		values.append(region['RegionName'])
	no = int(raw_input("Enter region Number: "))
	if no not in range(1, len(values)+1):
		print "Invalid option"
		exit()
	reply = raw_input( "You have selected " + values[no-1] + ", do you want to continue(Y/N): ")
	if reply == 'y' or reply =='Y':
		return values[no-1]
	else:
		exit()
#function to select ELB
def get_elb(client):
	elbs = client.describe_load_balancers()['LoadBalancerDescriptions']
        print "\t\tSelect ELB\n***********************************************"
        i = 1
        values = []	
	for elb in elbs:
		print str(i) + ". " + elb['LoadBalancerName']
		i += 1
		values.append(elb['LoadBalancerName'])
	no = int(raw_input("Enter ELB Number: "))
	if no not in range(1, len(values)+1):
        	print "Invalid option"
 		exit()
	reply = raw_input( "You have selected " + values[no-1] + ", do you want to continue(Y/N): ")
	access_log = client.describe_load_balancer_attributes(LoadBalancerName=values[no-1])['LoadBalancerAttributes']['AccessLog']
	if access_log['Enabled'] != True:
		print "For " + values[no-1] + " access logs are not enabled"
		exit()
        if reply == 'y' or reply =='Y':
                return [access_log['S3BucketName'],access_log['S3BucketPrefix'], values[no-1]]
        else:
                exit()
#sub function to find list of s3 objects which got modified for last 2 hours
def s3_objects(client, s3_name, log_prefix, elb_name, start, end):
	s3_keys = []
	marker = ''
	while True:
		objects = client.list_objects(Bucket=s3_name, Prefix = log_prefix ,Marker = marker)
		try:
			for object in objects['Contents']:
				if object['LastModified'].strftime('%Y/%m/%d %H:%M:%S') >= start and object['LastModified'].strftime('%Y/%m/%d %H:%M:%S') <= end and object['Key'].split('_')[3] == elb_name:
					s3_keys.append(object['Key'])
				marker = object['Key']
		except:
			break
		if objects['IsTruncated']  == False:
			break
	return s3_keys
#function to get s3 log paths in a specified time frame
def log_path(path, start, end):
	pattern = re.compile("[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]")
	if not pattern.match(start) and not pattern.match(end):
        	print "Entered start/end time is not in a proper format"
        	exit()
	prefix = []
	start1 = start.split(" ")[0]
	end1 = end.split(" ")[0]
	next1 = start1
	pattern = '%Y/%m/%d %H:%M:%S'
	epoch_start = int(calendar.timegm(time.strptime(start, pattern)))
	epoch_end = int(calendar.timegm(time.strptime(end, pattern)))
	epoch_next = epoch_start
	while end1>= next1:
        	prefix.append(path+next1)
        	epoch_next = epoch_next+24*3600
        	next1 = time.strftime("%Y/%m/%d", time.gmtime(epoch_next))
	return prefix
#function to get s3 file locations which got modified for last 2 hours
def log_files(client, s3_name, s3_prefix, account_id,region, elb_name):
	start = raw_input("Enter start date(YYYY/mm/dd HH:MM:SS) in UST: ")
	end = raw_input("Enter end date(YYYY/mm/dd HH:MM:SS) in UST: ")
	if s3_prefix:
		log_prefix = log_path(s3_prefix+'/AWSLogs/'+account_id+'/elasticloadbalancing/'+region+'/', start, end)
	else:
		log_prefix = log_path('AWSLogs/'+account_id+'/elasticloadbalancing/'+region+'/', start , end)
	s3_keys = []
	for i in log_prefix:
		s3_keys += s3_objects(client, s3_name, i, elb_name,start, end)
	return [s3_keys, start, end]
#function to downlod s3 logs to a file
def get_logs(client, s3_name, s3_keys, elb_name, start, end):
	logs = []
	if len(s3_keys) == 0:
		print "No logs are generated during the time frame"
	for key in s3_keys:
		with open('file.log', 'ab') as data:
			client.download_fileobj(s3_name , key, data)
	with open('file.log','rb') as data:
		for line in data:
			temp = line.split(" ")
			temp_time = temp[0].split('T')[0].replace('-','/') + ' '+ temp[0].split('T')[1].replace("Z","").split('.')[0]
			if temp_time > time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()-7200)) and elb_name == temp[1]:
				logs.append(line)
	os.remove('file.log')
	if len(logs) == 0:
		print "No logs are generated during the time frame"
		exit()
	return logs


##############################################################################
#   Steps to parse the logs and generate output in a user specified format   #
##############################################################################


#function to print all logs with follwing fields 
# 1. time stamp 2. client:port 3. backend: port 4. request_processing_time 5. backend processing time 6. response_processing_time
# 7. elb_status_code 8. backend_status_code 9. request
def list_required1(logs):
	print "Time_stamp\tclient:port\tbackend:port\tRequest_processing_time\tBackend_processing_time\tResponse_processing_time\tElb_status_code\tBackend_status_code\tRequest"
	for log in logs:
		temp = log.split(" ")
		print temp[0]+'\t'+temp[2]+'\t'+temp[3]+'\t'+temp[4]+'\t'+temp[5]+'\t'+temp[6]+'\t'+temp[7]+'\t'+temp[8]
		


#main function
cross_role = select_client(boto3.client('dynamodb','us-west-2'))
account_id = cross_role.split(':')[4]
region = get_region(boto3.client('ec2'))
assume_role = boto3.client('sts').assume_role(RoleArn=cross_role,RoleSessionName='Demo')
access_key = assume_role['Credentials']['AccessKeyId']
secret_key = assume_role['Credentials']['SecretAccessKey']
session_token = assume_role['Credentials']['SessionToken']
client = boto3.client('elb',region_name=region,aws_access_key_id=access_key,aws_secret_access_key=secret_key,aws_session_token=session_token)
log_location = get_elb(client)
client = boto3.client('s3', aws_access_key_id=access_key,aws_secret_access_key=secret_key,aws_session_token=session_token)
s3_keys = log_files(client, log_location[0], log_location[1], account_id, region, log_location[2])
logs = get_logs(client, log_location[0], s3_keys[0], log_location[2], s3_keys[1], s3_keys[2])
list_required1(logs)
