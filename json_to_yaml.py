#!/usr/bin/python

import os,sys
import json
import yaml
import shutil

if __name__ == "__main__":
  md_file = sys.argv[1]
  yaml_file = '.'.join(md_file.split('.')[:-1])+'-yaml.md'
  old_file = '.'.join(md_file.split('.')[:-1])+'-old.md'
  print('md_file:',md_file)

  script_home = os.path.dirname(os.path.realpath(__file__))
  print('script_home', script_home)

  with open(md_file, 'r') as f:
    md_contents = f.read()
  content = []

  current_comment = ''
  with open(yaml_file, 'w') as f:
      for line_number,line in enumerate(md_contents.split('\n')):
        if current_comment:
          current_comment += line
        elif line.startswith('[//]: # ('):
          # This code is DEPRECATED.
          # this line contains commented content. Parsing later.
          current_comment = line[9:]
          #print('current_comment',current_comment)
        else:
          f.write(line+'\n')
        if current_comment and current_comment[-1] == ')':
          # this and possibly preceding lines has contained commented content. Parse formatting json:
          current_comment = current_comment[:-1] # remove last parenthesis (markdown syntax)
          try:
            formatting = json.loads(current_comment)
            print('{}: formatting from json syntax: \n  {}'.format(line_number, yaml.dump(formatting).replace('\n', '\n  ')))
            f.write('---\n')
            f.write(yaml.dump(formatting))
            f.write('---\n')
          except Exception as e:
            print('failed to parse markdown comment as json. will write to file.',current_comment)
            f.write('[//]: # ('+current_comment+')\n')
          current_comment = '' # reset comment. Next line is not a continuation of a comment.

  print('os.rename(',md_file, old_file,')')
  os.rename(md_file, old_file)
  print('os.rename(',yaml_file, md_file,')')
  os.rename(yaml_file, md_file)

