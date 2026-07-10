import os, subprocess

def is_big_file(res_file):
	with open(res_file, "r") as fin:
		try:
			return "Google Drive - Virus scan warning" in fin.read()
		except UnicodeDecodeError:
			return False

def download(file_id, dest_dir, res_file, zipped=True):
	os.makedirs(dest_dir, exist_ok=True)
	subprocess.run("wget \"https://docs.google.com/uc?export=download&id="+ file_id +"\" -O "+ dest_dir+"/"+res_file, shell=True, check=True)
	if is_big_file(dest_dir+"/"+res_file):
		# Fixed 2026-07: Google Drive changed its virus-scan confirmation flow;
		# the old cookie/confirm-token extraction silently saved the HTML warning
		# page instead of the file. The modern download endpoint accepts confirm=t.
		os.remove(dest_dir+"/"+res_file)
		subprocess.run("wget \"https://drive.usercontent.google.com/download?export=download&confirm=t&id="+ file_id +"\" -O "+ dest_dir+"/"+res_file, shell=True, check=True)

	if zipped:
		os.system("unzip "+ dest_dir+"/"+res_file +" -d "+ dest_dir +"/")
		os.remove(dest_dir+"/"+res_file)
