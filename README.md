# BMS Database

面向浙江大学基础医学本科生的课程资料与学习经验网站。

这里收录课程考核信息、学习经验、讨论课与考试资料，并提供培养方案查阅入口。我们希望把分散的资料和往届记录整理在一起，方便后来者了解课程、安排学习和复习。

**网站入口：[BMS Database](https://bms-zju.github.io/BMS_Database/)**

## 内容与使用

- [课程资料](https://bms-zju.github.io/BMS_Database/courses/)：按课程名或课程号查阅考核信息、学习经验，以及已收录的讨论课、小测与考试资料。
- [培养方案](https://bms-zju.github.io/BMS_Database/curricula/)：按入学年级和班型，核对课程号、学分与建议学期。
- [使用说明](https://bms-zju.github.io/BMS_Database/guide/)：了解怎样查找资料、区分学年、阅读回忆卷和使用站外链接。

课程要求以对应学年的课程组通知为准，培养方案应对应自己的入学年级和班型。往届经验与考试回忆记录的是当时的情况，不能直接视为当前要求；阅读时请留意缺失、存疑和参考答案来源等说明。

## 贡献与纠错

发现内容错误、链接失效，或愿意提供学习记录与资料，可以从网站的[贡献与纠错](https://bms-zju.github.io/BMS_Database/contribute/)开始。内容可以是普通文字，不必先整理成网页；请说明课程、时间、来源和仍不确定的地方。

直接修改仓库时，请先阅读[贡献指南](CONTRIBUTING.md)，再按任务查阅[课程主页](COURSE_HOMEPAGE_GUIDE.md)、[试卷与小测](RECALL_PAPER_GUIDE.md)、[阅读体验](READING_EXPERIENCE_GUIDE.md)或[学期与校历参考](EXAM_SEMESTER_REFERENCE.md)等维护文档。

公开反馈中请勿包含个人隐私，也不要上传权限不明的原件。

## 资料使用与许可

本站资料免费供学习参考，欢迎分享本站页面链接。

- 使用时保留原有署名、来源链接和使用说明。
- 未经相关权利人许可，不得转载全文或重新上传文件；将完整资料转成图片、扫描件或其他文件后再发布，同样适用。
- 禁止将资料用于付费题库、出售资料包、收费课程配套材料等商业用途，本站不提供商业使用授权。
- 个人学习中的保存、笔记和打印，依具体材料的许可与法律规定处理。

具体材料已有有效许可或法律另有规定的，按其适用范围处理；上述说明不变更既有许可，也不扩大本站对第三方内容的授权。

仓库保留 [MIT 许可](LICENSE)。课程资料、字体和图标等如有单独的许可、署名或使用要求，应查看对应说明，不将所有第三方材料视为同一授权范围。完整说明见 [来源与使用范围](https://bms-zju.github.io/BMS_Database/contribute/sources-and-permissions/#resource-use)。

## 本地预览与开发

网站使用 MkDocs Material 构建。以下以 Windows PowerShell 为例，需预先安装 Git 和 Python 3.12。

首次获取项目并进入仓库根目录：

```powershell
git clone https://github.com/BMS-ZJU/BMS_Database.git
cd BMS_Database
```

已有本地仓库时，可跳过上面的命令，直接进入仓库根目录。以下命令均在仓库根目录运行。

创建独立环境、安装依赖并启动预览：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m mkdocs serve
```

启动后，在浏览器中打开终端显示的本地地址。

提交前建议运行严格构建：

```powershell
.\.venv\Scripts\python.exe -m mkdocs build --strict
```

常用位置：

- [docs/](docs/)：网站页面与公开资源。
- [mkdocs.yml](mkdocs.yml)：网站配置。
- [overrides/](overrides/) 与 [hooks/](hooks/)：主题模板与构建扩展。
