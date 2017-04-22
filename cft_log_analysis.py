import boto3
import time
import argparse
import calendar
import gzip

parser = argparse.ArgumentParser(usage= '%(prog)s [options]',description='******ELB_LOG_ANALYSIS******', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('--version', action = 'version', version = '%(prog)s 1.0.0')
parser.add_argument('-t','--time', type = float, help = 'Specify time in hours, fetch logs for last specified hours')



args = parser.parse_args()


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

def get_cft(client):
        i = 1
	next_marker = ''
	values = []
	while True:
		cfts = client.list_distributions(Marker=next_marker)['DistributionList']['Items']
	        if i == 1:
			print "\t\tSelect CFT\n***********************************************"
        	for cft in cfts:
                	print str(i) + ". " + cft['Id']
			i += 1
			values.append(cft['Id'])
		try:
			next_marker = cft['NextMarker']
		except:
			break
        no = int(raw_input("Enter CFT Number: "))
        if no not in range(1, i+1):
                print "Invalid option"
                exit()
        reply = raw_input( "You have selected " + values[no-1] + ", do you want to continue(Y/N): ")
        access_log = client.get_distribution(Id = values[no-1])['Distribution']['DistributionConfig']['Logging']
        if access_log['Enabled'] != True:
                print "For " + values[no-1] + " access logs are not enabled"
                exit()
        if reply == 'y' or reply =='Y':
                return [access_log['Bucket'],access_log['Prefix'], values[no-1]]
        else:
                exit()

#sub function to find list of s3 objects which got modified for specified hours
def s3_objects(client, s3_name, log_prefix, cft_id, start, end):
        s3_keys = []
        marker = ''
        while True:
                objects = client.list_objects(Bucket=s3_name, Prefix = log_prefix ,Marker = marker)
                try:
                        for object in objects['Contents']:
                                if object['LastModified'].strftime('%Y/%m/%d %H:%M:%S') >= start and object['LastModified'].strftime('%Y/%m/%d %H:%M:%S') <= end and object['Key'].split('.')[0] == cft_id:
                                        s3_keys.append(log_prefix+object['Key'])
                                marker = object['Key']
                except:
                        break
                if objects['IsTruncated']  == False:
                        break
        return s3_keys


#function to get s3 file locations which got modified for specified hours
def log_files(client, s3_name, s3_prefix, cft_id):
        pattern = '%Y/%m/%d %H:%M:%S'
        if args.time == None:
                start = raw_input("Enter start date(YYYY/mm/dd HH:MM:SS) in UTC: ").strip()
                end = raw_input("Enter end date(YYYY/mm/dd HH:MM:SS) in UTC: ").strip()
        else:
                start = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(time.time()-3600*args.time))
                end = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(time.time()))
        temp_end = time.strftime('%Y/%m/%d %H:%M:%S',  time.gmtime((int(calendar.timegm(time.strptime(end, pattern)))+7200)))
        s3_keys = []
	s3_keys = s3_objects(client, s3_name, s3_prefix, cft_id, start, temp_end)
        if len(s3_keys) == 0:
                print "There are no logs for the time you specified"
                exit()
        return [s3_keys, start, end]

#function to download log files for the specified time period
def get_logs(client, s3_name, s3_keys, start, end):
	logs = []
	file1 = str(time.time())+'.log1'
	print s3_name
	print s3_keys
	for s3_key in s3_keys:
		with open('file1', 'ab') as data:
			client.download_fileobj(s3_name, s3_key, data)
	f = gzip.open('filename','rb')
	data = f.read()	
	for line in data:
		print line


def main():
	#cross_role = select_client(boto3.client('dynamodb','us-west-2'))
	#assume_role = boto3.client('sts').assume_role(RoleArn=cross_role,RoleSessionName='Demo')
	#access_key = assume_role['Credentials']['AccessKeyId']
	#secret_key = assume_role['Credentials']['SecretAccessKey']
	#session_token = assume_role['Credentials']['SessionToken']
	#client = boto3.client('cloudfront',aws_access_key_id=access_key,aws_secret_access_key=secret_key,aws_session_token=session_token)
	client = boto3.client('cloudfront',aws_access_key_id=access_key,aws_secret_access_key=secret_key)
	log_location = get_cft(client)
	#client = boto3.client('s3', aws_access_key_id=access_key,aws_secret_access_key=secret_key,aws_session_token=session_token)
	client = boto3.client('s3', aws_access_key_id=access_key,aws_secret_access_key=secret_key)
	s3_keys = log_files(client, log_location[0][:-17], log_location[1], log_location[2])
	logs = get_logs(client, log_location[0], s3_keys[0], s3_keys[1], s3_keys[2])
	

if __name__ == '__main__':
    main()
#End of main function
