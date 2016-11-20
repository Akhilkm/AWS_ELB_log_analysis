import optparse

def fib(n, prin):
        a,b = 0,1
        for i in range(n):
                a,b = b, a+b
                if prin:
                        print a
        return a
def Main():
        parser = optparse.OptionParser('usage %prog '+\
                        '-n <fib number> -o <output file> -a (print all)', version = "%prog 1,0", epilog="Examples:\n check_dell -c all check_dell -c fans memory voltage check_dell -s")
        parser.add_option('-n','--number',dest = 'num', type ='int',\
                        default = 5,help="specify the n''thnfibonacci \n number to output")
        parser.add_option('-o', dest = 'out', type='string', \
                        help = 'specify an output file (Optional)')
        parser.add_option('-a','--all', action='store_true', dest='prin', \
                        default=False, help='print all numbers up to n')
        parser.add_option("-f", "--file", dest="filename",
                  help="write report to FILE", metavar="FILE")
	parser.add_option("-t","--test", dest='testing',action='store_const',help='testing')
        (options, args) = parser.parse_args()
        if (options.num == None):
                print parser.usage
                exit(0)
        else:
                number = options.num
	print options.filename
	print options.testing
        result = fib(number, options.prin)
        print "The "+ str(number) + "th fib number is " + str(result)

        if(options.out != None):
                f = open(options.out, "a")
                f.write(str(result) + "\n")

if __name__ == '__main__':
        Main()

