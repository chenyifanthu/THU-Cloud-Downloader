"""
https://github.com/chenyifanthu/THU-Cloud-Downloader
"""
import argparse
import os
import re
from tqdm import tqdm
import requests
import urllib.parse

sess = requests.Session()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--link', '-l', type=str, required=True, help='Share link of Tsinghua Cloud')
    parser.add_argument('--password', '-p', type=str, default='', help='Password of the share link')
    parser.add_argument('--save', '-s', type=str, default='./', help='Save directory')
    parser.add_argument('--file', '-f', type=str, default=None,
                        help='File name, support regex, if not set, download all files')
    return parser.parse_args()


def get_share_key(args):
    url = args.link
    prefix = 'https://cloud.tsinghua.edu.cn/d/'
    if not url.startswith(prefix):
        raise ValueError('Share link of Tsinghua Cloud should start with {}'.format(prefix))
    share_key = url[len(prefix):].replace('/', '')
    print('Share key: {}'.format(share_key))
    args.share_key = share_key


def verify_password(pwd: str, share_key: str):
    global sess

    r = sess.get(f"https://cloud.tsinghua.edu.cn/d/{share_key}/")
    pattern = '<input type="hidden" name="csrfmiddlewaretoken" value="(.*)">'
    csrfmiddlewaretoken = re.findall(pattern, r.text)
    if not csrfmiddlewaretoken:
        return

    # Verify password
    csrfmiddlewaretoken = csrfmiddlewaretoken[0]
    print("PASSWORD", pwd)
    r = sess.post(f"https://cloud.tsinghua.edu.cn/d/{share_key}/",
                  data={"csrfmiddlewaretoken": csrfmiddlewaretoken,
                        "token": share_key, "password": pwd},
                  headers={"Referer": f"https://cloud.tsinghua.edu.cn/d/{share_key}/"})
    # print(r.text)
    if "Please enter a correct password" in r.text:
        raise ValueError("Couldn't download files, please check your password.")
    elif "Please enter the password" in r.text:
        raise ValueError("This share link needs password.")


def dfs_search_files(share_key: str, path="/"):
    global sess
    filelist = []
    encoded_path = urllib.parse.quote(path)
    r = sess.get('https://cloud.tsinghua.edu.cn/api/v2.1/share-links/{}/dirents/?path={}'.format(share_key, encoded_path))
    objects = r.json()['dirent_list']
    for obj in objects:
        if obj["is_dir"]:
            filelist += dfs_search_files(share_key, obj['folder_path'])
        elif args.file is None:
            filelist.append(obj)
        else:
            mat = re.match(args.file.replace('*', '.*'), obj['file_name'])
            if mat is not None and mat.span()[1] == len(obj['file_name']):
                filelist.append(obj)
                continue
            mat = re.match(args.file.replace('*', '.*'), obj['file_path'])
            if mat is not None and mat.span()[1] == len(obj['file_path']):
                filelist.append(obj)
                continue
    return filelist


def download_single_file(url: str, fname: str):
    global sess
    resp = sess.get(url, stream=True)
    total = int(resp.headers.get('content-length', 0))
    with open(fname, 'wb') as file, tqdm(
            total=total,
            ncols=120,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)


def download(args):
    get_share_key(args)
    verify_password(args.password, args.share_key)

    print("Searching for files to be downloaded...")
    filelist = sorted(dfs_search_files(args.share_key), key=lambda x: x['file_path'])
    print("Found {} files in the share link.".format(len(filelist)))
    print("Last Modified Time".ljust(25), " ", "File Size".rjust(10), " ", "File Path")
    print("-" * 100)
    for file in filelist:
        print(file["last_modified"], " ", str(file["size"]).rjust(10), " ", file["file_path"])
    print("-" * 100)

    while True:
        key = input("Start downloading? [y/n]")
        if key == 'y':
            break
        elif key == 'n':
            return

    for i, file in enumerate(filelist):
        file_url = 'https://cloud.tsinghua.edu.cn/d/{}/files/?p={}&dl=1'.format(args.share_key, file["file_path"])
        save_path = os.path.join(args.save, file["file_path"][1:])
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        print("[{}/{}] Downloading File: {}".format(i + 1, len(filelist), save_path))
        try:
            download_single_file(file_url, save_path)
        except Exception as e:
            print("Error happened when downloading file: {}".format(save_path))
            print(e)

    print("Download finished.")


if __name__ == '__main__':
    """
    用法:
    python thu_cloud_download.py 
    -l https://cloud.tsinghua.edu.cn/d/1234567890/ 
    -s "~/path_to_save" 
    -f "*.pptx?" (regex, 正则表达式)
    """
    args = parse_args()
    download(args)
