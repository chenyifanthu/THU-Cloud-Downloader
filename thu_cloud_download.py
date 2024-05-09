import os
import re
import logging
import fnmatch
import requests
import argparse
import urllib.parse
from tqdm import tqdm


sess = requests.Session()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_args():
    args = argparse.ArgumentParser()
    args.add_argument('-l', '--link', type=str, required=True, help='Share link of Tsinghua Cloud')
    args.add_argument('-s', '--save_dir', type=str, default=None, help='Path to save the files. Default: Desktop')
    args.add_argument('-f', '--file', type=str, default=None, help='Regex to match the file path')
    return args.parse_args()


def get_share_key(url: str) -> str:
    prefix = 'https://cloud.tsinghua.edu.cn/d/'
    if not url.startswith(prefix):
        raise ValueError('Share link of Tsinghua Cloud should start with {}'.format(prefix))
    share_key = url[len(prefix):].replace('/', '')
    logging.info('Share key: {}'.format(share_key))
    return share_key


def get_root_dir(share_key: str) -> str:
    # Aquire the root directory name of the share link, 
    # run after verify_password function
    global sess
    pattern = '<meta property="og:title" content="(.*)" />'
    r = sess.get(f"https://cloud.tsinghua.edu.cn/d/{share_key}/")
    root_dir = re.findall(pattern, r.text)
    assert root_dir is not None, "Couldn't find title of the share link."
    logging.info("Root directory name: {}".format(root_dir[0]))
    return root_dir[0]


def verify_password(share_key: str) -> None:
    # Require password if the share link is password-protected,
    # and verify the password provided by the user.
    global sess
    r = sess.get(f"https://cloud.tsinghua.edu.cn/d/{share_key}/")
    pattern = '<input type="hidden" name="csrfmiddlewaretoken" value="(.*)">'
    csrfmiddlewaretoken = re.findall(pattern, r.text)
    if csrfmiddlewaretoken:
        pwd = input("Please enter the password: ")
        
        csrfmiddlewaretoken = csrfmiddlewaretoken[0]
        data = {
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "token": share_key,
            "password": pwd
        }
        r = sess.post(f"https://cloud.tsinghua.edu.cn/d/{share_key}/", data=data,
                    headers={"Referer": f"https://cloud.tsinghua.edu.cn/d/{share_key}/"})
        if "Please enter a correct password" in r.text:
            raise ValueError("Wrong password.")


def is_match(file_path: str, pattern: str) -> bool:
    # judge if the file path matches the regex provided by the user
    file_path = file_path[1:] # remove the first '/'
    return pattern is None or fnmatch.fnmatch(file_path, pattern)


def dfs_search_files(share_key: str, 
                     path: str = "/", 
                     pattern: str = None) -> list:
    global sess
    filelist = []
    encoded_path = urllib.parse.quote(path)
    r = sess.get(f'https://cloud.tsinghua.edu.cn/api/v2.1/share-links/{share_key}/dirents/?path={encoded_path}')
    objects = r.json()['dirent_list']
    for obj in objects:
        if obj["is_dir"]:
            filelist.extend(
                dfs_search_files(share_key, obj['folder_path'], pattern))
        elif is_match(obj["file_path"], pattern):
            filelist.append(obj)
    return filelist


def download_single_file(url: str, fname: str, pbar: tqdm):
    global sess
    resp = sess.get(url, stream=True)
    with open(fname, 'wb') as file:
        for data in resp.iter_content(chunk_size=1024):
            size = file.write(data)
            pbar.update(size)


def print_filelist(filelist):
    print("=" * 100)
    print("Last Modified Time".ljust(25), " ", "File Size".rjust(10), " ", "File Path")
    print("-" * 100)
    for i, file in enumerate(filelist, 1):
        print(file["last_modified"], " ", str(file["size"]).rjust(10), " ", file["file_path"])
        if i == 100:
            print("... %d more files" % (len(filelist) - 100))
            break
    print("-" * 100)
    
    
def download(share_key: str, filelist: list, save_dir: str) -> None:
    if os.path.exists(save_dir):
        logging.warning("Save directory already exists. Files will be overwritten.")
    total_size = sum([file["size"] for file in filelist])
    pbar = tqdm(total=total_size, ncols=120, unit='iB', unit_scale=True, unit_divisor=1024)
    for i, file in enumerate(filelist):
        file_url = 'https://cloud.tsinghua.edu.cn/d/{}/files/?p={}&dl=1'.format(share_key, file["file_path"])
        save_path = os.path.join(save_dir, file["file_path"][1:])
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        # logging.info("[{}/{}] Downloading File: {}".format(i + 1, len(filelist), save_path))
        try:
            pbar.set_description("[{}/{}]".format(i + 1, len(filelist)))
            download_single_file(file_url, save_path, pbar)
            
        except Exception as e:
            logging.error("Error happened when downloading file: {}".format(save_path))
            logging.error(e)
    pbar.close()
    logging.info("Download finished.")



def main():
    args = parse_args()
    url, pattern, save_dir = args.link, args.file, args.save_dir
    share_key = get_share_key(url)
    verify_password(share_key)
    
    # search files
    logging.info("Searching for files to be downloaded, Wait a moment...")
    filelist = dfs_search_files(share_key, pattern=pattern)
    filelist.sort(key=lambda x: x["file_path"])
    if not filelist:
        logging.info("No file found.")
        return

    print_filelist(filelist)
    total_size = sum([file["size"] for file in filelist]) / 1024 / 1024 # MB
    logging.info(f"# Files: {len(filelist)}. Total size: {total_size: .1f} MB.")
    key = input("Start downloading? [y/n]")
    if key != 'y':
        return
    
    # Save to desktop by default.
    if save_dir is None:
        save_dir = os.path.join(os.path.expanduser("~"), 'Desktop')
        assert os.path.exists(save_dir), "Desktop folder not found."
    root_dir = get_root_dir(share_key)
    save_dir = os.path.join(save_dir, root_dir)
    
    download(share_key, filelist, save_dir)
    
    
    
if __name__ == '__main__':
    """
    用法:
    python main.py \
    -l https://cloud.tsinghua.edu.cn/d/1234567890/ \
    -s "~/path_to_save" \
    -f "*.pptx?" (regex, 正则表达式) \
    """
    main()
