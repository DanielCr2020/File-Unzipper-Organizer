# Daniel Craig
#
# Python program to unzip files and put them into a specific folder. Intended for Stevens CS 546 to make running moss easier. Could also be used for other stuff
# When it is done running, all the files to run in moss will be put in argv[1]/allSubmissions
# Usage: python organizeSubmissions.py <path_to_target_folder> <path_to_zips_folder>
# 
# argv[1]: path_to_target_folder: A new folder will be created here. All the unzipped files will go in that folder
# argv[2]: path_to_zips_folder: is the relative path to the folder that contains all the zip files
#
# Beforehand, make sure you download all the submission zips and put them in a folder. The path to this folder is path_to_zips_folder
# The submissions zip structure is from canvas
# In it's current state, the structure must be a folder containing zip files that contain zip files
# Still (probably) a work in progress at the moment (I spent *way* too much time on this so far...)
#
# Platforms: 
# WSL2: Works, but quite slow due if used with the Windows filesystem. 
# WSL1: Works and is ~10x faster than WSL2
# Powershell: Doesn't really work. Files aren't deleted properly. This may be due to shutil
# Other platforms: idk lol
#
#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
#include <unistd.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>

import zipfile as zippy
import sys, os, shutil, time
from pathlib import Path

file_filter_type="except"
# file_filter_type: 
# 1. "only":     Only include certain files (listed in file_inclusions) from the student zips in the target folder
# 2. "except":   Include all files (except those listed in file_exclusions) from the student zips in the target folder
# 3. "all":      Include all files from the student zips in the target folder (Probably not a great idea)
# 4. "ext":      Only keep files with a certain extension
# 5. "ext-test": Only keep files with a certain extension, but remove files with '.test' in the name
# 6. "true-all": always_delete does not apply here. ALL files are kept (BAD idea. Will keep node_modules and .git folders)

file_exclusions=["lab1.test.mjs","._lab1.mjs","._lab1.js","._lab1.test.mjs","__MACOSX",".git","._.git"] # files to not include in the zip
file_inclusions=["lab1.mjs","lab1.js"]    # files to include
always_delete=["__MACOSX",".git",".DS_Store","._.DS_Store","._.git"] # Delete these files no matter what
extensions=["mjs","js"]     #Extensions to preserve
teststring=".test"

if len(sys.argv) != 3:
    print("Usage: python organizeSubmissions.py <path_to_target_folder> <path_to_zips_folder>")
    sys.exit(1)
start=time.time()
print("File filter type:",file_filter_type)
folder_path = sys.argv[1]       #Path to target folder for all the submissions to go
zip_path = sys.argv[2]          #Path to folder where the downloaded canvas zips are stored

# Ensure trailing '/' exists
folder_path = folder_path if folder_path[-1]=='/' else folder_path+'/' 
zip_path = zip_path if zip_path[-1]=='/' else zip_path+'/'

folder_path+='allSubmissions'

try:        # making the target directory for all the submissions
    shutil.rmtree(folder_path)
    os.mkdir(folder_path)
except:
    pass

unzipped_count=0        #unzip all the files
for zips in os.listdir(zip_path):
    with zippy.ZipFile(zip_path+zips,"r") as zip_file:
        for file_name in zip_file.namelist():
            zip_file.extract(file_name, folder_path)
            unzipped_count+=1

print(f'Unzipped {unzipped_count} file{"s" if unzipped_count!=1 else ""} from {zip_path} to {folder_path}')

try:        
    os.mkdir(folder_path+'/temp')        # Extract one zip file at a time into here, rename the files, and then handle the rest accordingly
    os.mkdir(folder_path+'/moss-ready')  # the files in this folder are ready to be mossed
except:
    pass

def delete(path):
    '''Deletes a file. If the file is a folder, deletes the whole folder'''
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except:
        pass

def flatten(directory):     #Works, but may skip files that are the same name
    '''Flattens a directory. Takes all files in sub-dorectories and brings them to the top level'''
    for dirpath, _, filenames in os.walk(directory, topdown=False):
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            target = os.path.join(directory, filename)
            if source!=target:
                try:
                    shutil.move(source, target)
                except:
                    pass
        if dirpath != directory:        # removing empty directories
            os.rmdir(dirpath)

#the path stuff is inspired from here: https://csatlas.com/python-list-directory/
def search_and_destroy(path, filter):
    '''Recursively searches for files to delete. Deletes files according to specified filter'''
    if filter!='true-all':
        for p in Path(path).rglob('*'):     # rglob('*') recursively lists all the files
            if str(p).split('/')[-1] in always_delete:  #Recursively delete all files that match always_delete
                delete(str(p))
    if filter=="only":                              #Delete all files that don't match file_inclusions
        for p in Path(path).rglob('*'):
            if str(p).split('/')[-1] not in file_inclusions and os.path.isdir(str(p))==False:
                delete(str(p))
    elif filter=="except":                          #Only delete files that match file_exclusions
        for p in Path(path).rglob('*'): 
            if str(p).split('/')[-1] in file_exclusions and os.path.isdir(str(p))==False:
                delete(str(p))
    elif filter=="all":        #We keep all files here (except always_delete, which we already took care of, so do nothing)
        pass
    elif filter=="ext":                             #Only keep files whose extension matches extensions
        for p in Path(path).rglob('*'):
            if str(p).split('.')[-1] not in extensions and os.path.isdir(str(p))==False:
                delete(str(p))
    elif filter=="ext-test":                        #Same as above, but delete files with teststring in the name
        for p in Path(path).rglob('*'):
            if (str(p).split('.')[-1] not in extensions or teststring in str(p).split('/')[-1]) and os.path.isdir(str(p))==False:
                delete(str(p))

# Now that we have the submission zips from all sections in one folder, lets process them
# This code is incredibly stupid. TODO: make less stupid
def handle_files():
    '''Filters files, and moves them to the moss folder.'''
    moss_ready_count=0
    for submission_zips in os.listdir(folder_path):
        if submission_zips[-4:]==".zip":        #only use .zip files
            with zippy.ZipFile(folder_path+'/'+submission_zips,"r") as each_zip:
                for file_name in each_zip.namelist():
                    each_zip.extract(file_name,folder_path+'/temp')
                    search_and_destroy(folder_path+'/temp',file_filter_type)
                    flatten(folder_path+'/temp')                    #take files out of nested folders
                    search_and_destroy(folder_path+'/temp',file_filter_type)    #in case any spicy files got left behind
                    for files in os.listdir(folder_path+'/temp'):   #I have no idea why I need this
                        newpath = folder_path+'/temp/'+files        
                    for filtered_files in os.listdir(folder_path+'/temp'):
                        #now the temp folder has only the files we want
                        newname = folder_path+'/temp/'+submission_zips.split('_')[0]+'_'+filtered_files
                        try:
                            os.rename(newpath,newname)
                            shutil.move(newname,folder_path+'/moss-ready/')
                            moss_ready_count+=1
                        except:
                            pass
        if moss_ready_count%10==0 or moss_ready_count==unzipped_count:
            print(f"{moss_ready_count}/{unzipped_count} files are in the moss-ready folder")


handle_files()

#get rid of temp folder at end
shutil.rmtree(folder_path+"/temp")
end=time.time()
print(f"Done in {round(end-start,2)} seconds")





























# What are you doing down here? The code is up there! :3