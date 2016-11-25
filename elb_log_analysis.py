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
import requests



working_dir = os.getcwd()+'/'

###########################################################
#  Passing paramerts to the code                          # 
###########################################################

parser = optparse.OptionParser(version = 'elb-log-analysis 1.0.0')
parser.add_option('-t','--time',dest = 'spec_time', type ='float', help = 'Specify time in hours, fetch logs for last specified hours')
parser.add_option('-o','--output', dest = 'output_file', type ='string', help = 'Specify the output file name(avoid this option will print the output in cosole)')
parser.add_option('-r','--result', dest = 'result', type='string',default='latency', help = 'Specify the type of result latency 4xx 5xx source_5xx source_4xx source_3xx source_2xx invalid all')
parser.add_option('-c','--custom', dest = 'custom', type='string', help = 'Specify the custom columns separated by coma')

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
	pattern = '%Y/%m/%d %H:%M:%S'
	if options.spec_time == None:
		start = raw_input("Enter start date(YYYY/mm/dd HH:MM:SS) in UTC: ")
		end = raw_input("Enter end date(YYYY/mm/dd HH:MM:SS) in UTC: ")
	else:
		start = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(time.time()-3600*options.spec_time))
		end = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(time.time()))
	temp_end = time.strftime('%Y/%m/%d %H:%M:%S',  time.gmtime((int(calendar.timegm(time.strptime(end, pattern)))+3600)))
	if s3_prefix:
		log_prefix = log_path(s3_prefix+'/AWSLogs/'+account_id+'/elasticloadbalancing/'+region+'/', start, temp_end)
	else:
		log_prefix = log_path('AWSLogs/'+account_id+'/elasticloadbalancing/'+region+'/', start , temp_end)
	s3_keys = []
	for i in log_prefix:
		s3_keys += s3_objects(client, s3_name, i, elb_name,start, temp_end)
	if len(s3_keys) == 0:
		print "There are no logs for the time you specified"
		exit()
	return [s3_keys, start, end]
#function to downlod s3 logs to a file and will return logs as a list
def get_logs(client, s3_name, s3_keys, elb_name, start, end):
	logs = []
	if len(s3_keys) == 0:
		print "No logs are generated during the time frame"
	if os.path.isfile("file.log"):
		os.remove("file.log")
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

#function: select *(max(sort_column)) from list group_by(group_column) result will be in a sorted order and count will also added
def sort_group(check_list, sort_column, group_column):
        check_list = sorted(check_list, key=lambda x: (float(x[sort_column-1])), reverse=True)
        new_list = []
        temp_list = []
        for check in check_list:
                temp = check[group_column-1]
                if temp not in temp_list:
                        temp_list.append(temp)
                else:
                        continue
                count = 0
                for check1 in check_list:
                        if temp == check1[group_column-1]:
                                count += 1
                check.append(count)
                new_list.append(check)
        return new_list

#function to groupby elbstatus code and request url
def code_group(check_list, group1, group2, pattern):
	new_list = []
	temp_list = []
	for check in check_list:
		temp = check[group1-1]
		if temp not in temp_list and pattern.match(check[group2-1]):
			temp_list.append(temp)
		else:
			continue
		count = 0
		for check1 in check_list:
			if check1[group1-1] == temp and pattern.match(check1[group2-1]):
				count += 1
		check.append(count)
		new_list.append(check)
	return new_list
			

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
def list_statuscode(logs, pattern):
        logs_xx = []
	for log in logs:
                temp = log.split(" ")
                client_ip = temp[2].split(":")[0]
                logs_xx.append([client_ip, temp[7]])
        last = sorted(code_group(logs_xx, 1, 2, pattern), key=lambda x: (int(x[2]), x[0]), reverse=True)
	output = []
	for i in last:
		country = '-'
		org = '-'
		try:
			a = requests.get('http://ipinfo.io/'+i[0]).json()
			country = a['country']
			org = a['org']
		except:
			pass
		i.append(country)
		i.append(org)
		output.append(i)
        if options.output_file == None:
                print "Client_IP\tElb_status_code\tCount\tCountry_Code\tOrganisation"
                for i in output:
                        print i[0]+'\t'+i[1]+'\t'+str(i[2])+'\t'+i[3]+'\t'+i[4]
        else:
                with open(working_dir+options.output_file, "w") as f:
                        f.write("Client_IP,Elb_staus_code,Count,Country_code,Organisation\n")
                        for i in output:
                                f.write(i[0]+','+i[1]+','+str(i[2])+','+i[3]+','+i[4]+'\n')


#sl_no, source_ip, count_4xx group by sourceip and and sort by count
def parameter_4xx(logs):
        pattern = re.compile("4[0-9][0-9]")
        elb_statuscode = []
        for log in logs:
                temp = log.split(" ")
                elb_statuscode.append([temp[11]+" "+temp[12]+" "+temp[13],float(temp[4]),float(temp[5]),float(temp[6]),temp[7]])
        output = code_group(elb_statuscode,1,5,pattern)
        if options.output_file == None:
                print "Request_Url\tRequest_Processing_Time\tBackend_Processing_Time\tResponse_Processing_Time\tELB_Status_Code\tCount"
                for i in output:
                        print i[0]+'\t'+str(i[1])+'\t'+str(i[2])+'\t'+str(i[3])+'\t'+i[4]+'\t'+str(i[5])
        else:
                with open(working_dir+options.output_file, "w") as f:
                        f.write("Request_Url,Request_Processing_Time,Backend_Processing_Time,Response_Processing_Time,ELB_Status_Code,Count\n")
                        for i in output:
                                f.write(i[0]+','+str(i[1])+','+str(i[2])+','+str(i[3])+','+i[4]+','+str(i[5])+'\n')


#function to print logs with followting fields.
#sl_no, source_ip, count_5xx group by sourceip and and sort by count
def parameter_5xx(logs):
	pattern = re.compile("5[0-9][0-9]")
        elb_statuscode = []
	for log in logs:
                temp = log.split(" ")
                elb_statuscode.append([temp[11]+" "+temp[12]+" "+temp[13],float(temp[4]),float(temp[5]),float(temp[6]),temp[7]])
        output = code_group(elb_statuscode,1,5,pattern)
        if options.output_file == None:
		print "Request_Url\tRequest_Processing_Time\tBackend_Processing_Time\tResponse_Processing_Time\tELB_Status_Code\tCount"
                for i in output:
			print i[0]+'\t'+str(i[1])+'\t'+str(i[2])+'\t'+str(i[3])+'\t'+i[4]+'\t'+str(i[5])
        else:
                with open(working_dir+options.output_file, "w") as f:
                        f.write("Request_Url,Request_Processing_Time,Backend_Processing_Time,Response_Processing_Time,ELB_Status_Code,Count\n")
                        for i in output:
                                f.write(i[0]+','+str(i[1])+','+str(i[2])+','+str(i[3])+','+i[4]+','+str(i[5])+'\n')



#function to print logs with following fields.
#Sl_no, request_time, back_time, resp_time
def parameter_latency(logs):
	latency = []
	for log in logs:
		temp = log.split(" ")
		latency.append([temp[11]+" "+temp[12]+" "+temp[13],float(temp[4]),float(temp[5]),float(temp[6]),temp[7]])
	output = sort_group(latency,3,1)
	if options.output_file == None:
		print "Request_Url\tRequest_Processing_Time\tBackend_Processing_Time\tResponse_Processing_Time\tELB_Status_Code\tCount"
		for i in output:
			print i[0]+'\t'+str(i[1])+'\t'+str(i[2])+'\t'+str(i[3])+'\t'+i[4]+'\t'+str(i[5])
	else:
		with open(working_dir+options.output_file, "w") as f:
			f.write("Request_Url,Request_Processing_Time,Backend_Processing_Time,Response_Processing_Time,ELB_Status_Code,Count\n")
			for i in output:
				f.write(i[0]+','+str(i[1])+','+str(i[2])+','+str(i[3])+','+i[4]+','+str(i[5])+'\n')
	
	

################################################################################
#                             main function                                    # 
################################################################################

#Getting elb logs for the time specified
def main():
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

	if options.result and options.custom:
		print "Both custom and result can't use simultaniously"
	elif options.result=='latency' or (not options.result and not options.custom):
		parameter_latency(logs)
	elif options.result=='5xx':
		parameter_5xx(logs)
	elif options.result=='4xx':
		parameter_4xx(logs)
	elif options.result=='source_4xx':
		list_statuscode(logs,re.compile("4[0-9][0-9]"))
	elif options.result=='source_5xx':
        	list_statuscode(logs, re.compile("5[0-9][0-9]"))
	elif options.result=='source_3xx':
        	list_statuscode(logs,re.compile("3[0-9][0-9]"))
	elif options.result=='source_2xx':
        	list_statuscode(logs,re.compile("2[0-9][0-9]"))
	elif options.result=='invalid':
        	list_statuscode(logs,re.compile("^-$"))
	elif options.custom:
		a=1
	else:
		print "Wrong option given."


if __name__ == '__main__':
    main()
