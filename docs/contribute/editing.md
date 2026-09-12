---
title: 直接修改与提交 PR
comments: false
---

# 直接修改与提交 PR

熟悉 GitHub、能把内容改成网页的同学，推荐直接修改后提交 Pull Request（PR，合并请求）。这样可以准确表达想改的内容，也方便逐行审阅。只想提供原件、零散经验或报告问题时，用[投稿表单](submit.md)即可，不必先学 Git。

相关修改涉及多门课程或多个页面，可以放在同一个分支、同一个 PR 中；不需要逐页开 PR。

## 只改一个页面：在浏览器中完成

1. 登录 GitHub，在网站目标页面点击右上角铅笔图标，或页底的“直接编辑本页”。
2. GitHub 会打开对应的 Markdown 文件。没有仓库写入权限时，按提示 **Fork this repository**，在自己的副本中修改。
3. 修改文字，点击 **Preview** 看基本排版。Markdown 链接写作 <code>&#91;显示文字&#93;(目标地址)</code>；站内文件优先沿用现有相对路径。
4. 点击 **Commit changes** 或 **Propose changes**，填写简短说明，如“修复神经科学笔记链接”。有仓库写入权限时，也请选择新分支，再提交 PR。
5. 在 PR 页面确认目标是 **BMS-ZJU/BMS_Database 的 main 分支**，检查 **Files changed** 中只有本次想改的内容，再点击 **Create pull request**。

这些是 GitHub 的[网页编辑流程](https://docs.github.com/en/repositories/working-with-files/managing-files/editing-files)。按钮会随账号权限有所不同。GitHub 的 Preview 不能显示本站全部组件；涉及表格、折叠答案、打印或页面布局时，需要本站构建预览。

## 多页修改：使用同一分支

先 [Fork 本仓库](https://github.com/BMS-ZJU/BMS_Database/fork)，在自己的仓库中从最新 main 新建分支，例如 <code>update/course-resources</code>。在该分支依次修改相关文件，每次提交都选择这个分支，最后向原仓库 main 提交一个 PR。

也可以在仓库页面按 <code>.</code> 打开 [github.dev 网页编辑器](https://docs.github.com/en/codespaces/the-githubdev-web-based-editor)，集中编辑多个文件，通过左侧 Source Control 查看差异并提交到同一个分支。它可以编辑文件，但不能运行本站构建命令。

PR 已经打开后，继续修改原来的分支即可更新同一个 PR。维护者提出建议时，在该 PR 中回复或继续提交；不用重新创建另一份。

## 页面和资料放在哪里

最容易的定位方法是从目标网页点击编辑按钮。如果只有课程中文名，先查仓库中的 [COURSE_NAME_MAP.yml](https://github.com/BMS-ZJU/BMS_Database/blob/main/COURSE_NAME_MAP.yml)：<code>course_code</code> 用于区分课程，<code>path</code> 是 <code>docs/</code> 下的目录。

| 要修改或新增的内容 | 仓库位置 |
| --- | --- |
| 课程主页 | 对应课程目录的 <code>index.md</code> |
| 考试、回忆卷 | 课程目录的 <code>exams/</code> |
| 小测 | 课程目录的 <code>quizzes/</code> |
| 讨论课 | 课程目录的 <code>discussions/</code> |
| 可公开下载的原文件 | 课程目录的 <code>downloads/</code> |
| 页面专用图片 | 课程目录的 <code>assets/</code> |
| 全站菜单和页面入口 | 根目录 <code>mkdocs.yml</code> 中的 <code>nav</code> |

<code>mandatory/</code>、<code>elective/</code> 是保留的旧路径，不能据此判断某年级的必修或选修属性。不要为这次修改顺手重命名课程目录。

新增资料时，先找同类资料页作为格式参考，在对应目录添加文件，再补分组 <code>index.md</code> 的链接；需要出现在菜单中的页面还要更新 <code>mkdocs.yml</code>。已有链接的页面可以小范围原位修正。没有来源支持的栏目可以省略，不要套用已停用的课程主页模板。

## 内容怎样才便于收录

课程事实要有通知、原材料或明确经历作为依据，写清适用学年、年级或班型。新学年的考核变化应保留适用范围，不直接抹掉往年的记录。回忆卷缺题、缺图、存疑之处照实保留，不补成自认为正确的答案。

PR 说明简要写“改了什么、依据在哪里、哪些仍不确定”。原件有页码时请给页码；经验请说明作者与修读时间。只写允许公开的署名和来源线索，隐私证据先通过已确认的非公开渠道核对。文件加入公开分支后就已经公开，不能等合并时才考虑[来源与使用范围](sources-and-permissions.md)。

根据修改类型，继续阅读相应规范：

- [贡献指南](https://github.com/BMS-ZJU/BMS_Database/blob/main/CONTRIBUTING.md)：证据、目录、链接和提交要求
- [课程主页维护指南](https://github.com/BMS-ZJU/BMS_Database/blob/main/COURSE_HOMEPAGE_GUIDE.md)：课程信息、经验和资料入口的组织
- [回忆卷制作规范](https://github.com/BMS-ZJU/BMS_Database/blob/main/RECALL_PAPER_GUIDE.md)：试卷、小测、折叠答案和打印
- [学期与校历参考](https://github.com/BMS-ZJU/BMS_Database/blob/main/EXAM_SEMESTER_REFERENCE.md)：学年和考试时间的核对
- [阅读体验维护指南](https://github.com/BMS-ZJU/BMS_Database/blob/main/READING_EXPERIENCE_GUIDE.md)：字体、组件和屏幕／打印效果

## 需要完整预览时

使用 Python 3.12。在自己 Fork 的仓库副本根目录执行以下命令；Windows PowerShell 可直接使用：

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m mkdocs serve
~~~

浏览器打开终端给出的本地地址，检查修改后的页面和相关链接。完成后在终端按 Ctrl+C 停止预览，再执行：

~~~powershell
.\.venv\Scripts\python.exe -m mkdocs build --strict
git diff --check
~~~

纯文字修改先检查差异与链接；新增页面、导航或调整排版时，运行严格构建并检查手机宽度下的显示。调整小测或打印功能时还要核对实际打印稿。预览输出、临时文件和原始私有材料不要提交。

新增或修改课程映射后，还需运行 <code>python scripts/contributions/catalog.py --write</code>，将更新后的四份 GitHub 表单一起提交。普通页面新增、改名和链接更新会在构建时自动更新站内投稿页面列表。

## 提交后会发生什么

PR 会保留逐行差异供维护者审核，GitHub Actions 会尝试构建网站。首次贡献者的工作流可能需要维护者允许运行。构建通过说明页面可以生成，课程事实与资料使用范围仍需要核对。

维护者合并并完成部署后，修改才会出现在正式网站。投稿和直接 PR 都需要人工审核；直接修改不要求先经过 AI 整理。
