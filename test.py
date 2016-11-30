from optparse import OptionParser


parser = OptionParser()
parser.add_option('--s',
                  dest='s',
                  type='string',
                  help='''With triple quotes I can directly put in anything including line spaces.\n will appear as a string rather than a newline.''')
(options, args) = parser.parse_args()
print options.s
