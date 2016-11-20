#function: select *(max(sort_column)) from list group_by(group_column) result will be in a sorted order
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



a=[[1,'akhil',100],[2,'akhil',300],[3,'joseph',799],[4,'sumith',2323],[5,'akhil',234],[6,'sumith',2332],[7,'annan',3232],[8,'anjali',2344],[9,'joseph',23324],[10,'baby',2345],[11,'saf',23324],[12,'akhil',3223],[13,'annan',2332],[14,'joseph',32232],[15,'karthik',323],[16,'guru',2],[17,'alsa',2332],[18,'alsa',2334],[19,'chiro',233],[20,'saf',2345],[21,'pavan',23],[22,'gunda',23]]

for i in a:
	print i
k = sort_group(a,3,2)
print "final"
for i in k:
	print i
