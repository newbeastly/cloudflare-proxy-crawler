# 1. 配置Git全局身份
git config --global user.email "2287985686@qq.com"
git config --global user.name "newbeastly"
# 2. 初始化仓库并推送（需先在GitHub创建空仓库）
cd D:/Pycharm项目/爬虫/

git init
git add .
git commit -m "Initial commit"

# 将默认分支重命名为main
git branch -M main

# 关联远程仓库（替换your-username为你的GitHub用户名）
git remote add origin git@github.com:newbeastly/cloudflare-proxy-crawler.git

# 首次推送需要-u参数建立追踪关系
git push -u origin main
