##########################################################################################
#                         Python script to parse elb logs and find                       #
#				urls causing 4xx/5xx errrors                             #
#                                     Version 1.0.0                                      #
##########################################################################################



import boto3
import time
import os
import re
import calendar
import optparse



###########################################################
#  Passing paramerts to the code                          # 
###########################################################

parser = optparse.OptionParser(version = 'elb-log-analysis 1.0.0')
parser.add_option('-t','--time',dest = 'spec_time', type ='float', help = 'Specify time in hours, fetch logs for last specified hours')
parser.add_option('-o','--output', dest = 'output_file', type ='string', help = 'Specify the output file name(avoid this option will print the output in cosole)')
parser.add_option('-r','--result', dest = 'result', type='string', help = 'Specify the type of result latency 4xx 5xx')

(options, args) = parser.parse_args()




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
	if options.spec_time == None:
		start = raw_input("Enter start date(YYYY/mm/dd HH:MM:SS) in UST: ")
		end = raw_input("Enter end date(YYYY/mm/dd HH:MM:SS) in UST: ")
	else:
		start = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(time.time()-3600*options.spec_time))
		end = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(time.time()))
	if s3_prefix:
		log_prefix = log_path(s3_prefix+'/AWSLogs/'+account_id+'/elasticloadbalancing/'+region+'/', start, end)
	else:
		log_prefix = log_path('AWSLogs/'+account_id+'/elasticloadbalancing/'+region+'/', start , end)
	s3_keys = []
	for i in log_prefix:
		s3_keys += s3_objects(client, s3_name, i, elb_name,start, end)
	if len(s3_keys) == 0:
		print "There are no logs for the time you specified"
		exit()
	return [s3_keys, start, end]
#function to downlod s3 logs to a file and will return logs as a list
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
def list_all_fields(logs):
	print "Time_stamp\tclient:port\tbackend:port\tRequest_processing_time\tBackend_processing_time\tResponse_processing_time\tElb_status_code\tBackend_status_code\tRequest"
	for log in logs:
		temp = log.split(" ")
		print temp[0]+'\t'+temp[2]+'\t'+temp[3]+'\t'+temp[4]+'\t'+temp[5]+'\t'+temp[6]+'\t'+temp[7]+'\t'+temp[8]
		

#function to print logs with followting fields.
#sl_no, source_ip, count_4xx group by sourceip and and sort by count
def list_4xx(logs):
	sl_no = 0
	pattern = re.compile("4[0-9][0-9]")
	client_ips = []
	logs_4xx = []
	for log in logs:
		temp = log.split(" ")
		if pattern.match(temp[7]):
			client_ips.append(log.split(" ")[2].split(":")[0])
			logs_4xx.append(log)
	client_ips = list(set(client_ips))
	last = []
	for client_ip in client_ips:
		count = 0
		for log_4xx in logs_4xx:
			temp = log_4xx.split(" ")
			if temp[2].split(":")[0] == client_ip:
				count += 1
		last.append([client_ip, str(count)])
	sort_last = sorted(last, key=lambda x: (int(x[1]), x[0]), reverse=True)
	print "Sl_No\tClient_Ip\tCount"
	for i in sort_last:
		sl_no +=1
		print str(sl_no) +'\t'+i[0] +'\t'+i[1]
#function to print logs with followting fields.
#sl_no, source_ip, count_5xx group by sourceip and and sort by count
def list_5xx(logs):
        sl_no = 0
        pattern = re.compile("5[0-9][0-9]")
        client_ips = []
        logs_5xx = []
        for log in logs:
                temp = log.split(" ")
                if pattern.match(temp[7]):
                        client_ips.append(log.split(" ")[2].split(":")[0])
                        logs_5xx.append(log)
        client_ips = list(set(client_ips))
        last = []
        for client_ip in client_ips:
                count = 0
                for log_5xx in logs_5xx:
                        temp = log_5xx.split(" ")
                        if temp[2].split(":")[0] == client_ip:
                                count += 1
                last.append([client_ip, str(count)])
	sort_last = sorted(last, key=lambda x: (int(x[1]), x[0]), reverse=True)
        print "Sl_No\tClient_Ip\tCount"
        for i in sort_last:
                sl_no +=1
                print str(sl_no) +'\t'+i[0] +'\t'+i[1]
#function to print logs with following fields.
#Sl_no, request_time, back_time, resp_time
def list_latency(logs):
	sl_no = 0
	latency = []
	f = open("output.txt",'w')
	for log in logs:
		temp = log.split(" ")
		if float(temp[5]) > 2.0:
			source = temp[14] + ' ' + temp[15]+' '+temp[16]+' '+temp[17]
			source = source.partition('"')[-1].rpartition('"')[0]
			latency.append([temp[0],temp[1],temp[2].split(":")[0],temp[4],temp[5],temp[6],temp[7],temp[11]+' '+temp[12]+' '+temp[13]],source)
	sort_last = sorted(latency, key=lambda x: (float(x[4])), reverse=True)
	for last in sort_last:
		f.write(last[0]+','+last[1]+','+last[2]+','+last[3]+','+last[4]+','+last[5]+','+last[6]+','+last[7]+last[8]+'\n')
	f.close()		
	


################################################################################
#                             main function                                    # 
################################################################################

#Getting elb logs for the time specified
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


list_4xx(logs)
list_5xx(logs)
#parsing elb logs for the time specified
#if options.result == '4xx':
#	list_4xx(logs)
#elif options.result == '5xx':
#	list_5xx(logs)
#elif options.result == 'latency':
#	list_latency(logs)
#elif options.result == 'custom'
#	if options.

#else:
#	exit()
