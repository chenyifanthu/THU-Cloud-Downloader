# Tsinghua Cloud Downloader
根据清华云盘的分享链接批量下载文件。支持文件夹递归下载、大文件下载、指定特殊文件下载。

## Dependency
    pip install tqdm

## Usage
- Show optional arguments
```
    python main.py -h
```
- Download ALL files in the link to the current directory
```
    python main.py -l https://cloud.tsinghua.edu.cn/d/f2e1626da4f3404d87ab/
```

- Download ALL files to a specific directory
```
    python main.py -l https://cloud.tsinghua.edu.cn/d/f2e1626da4f3404d87ab/ -s /data/chenyifan/
```

- Download files end with .jpg
```
    python main.py -l https://cloud.tsinghua.edu.cn/d/f2e1626da4f3404d87ab/ -s /data/chenyifan/ -f *.jpg
```

## Output Log Example
<img src="example.jpg" width=800>