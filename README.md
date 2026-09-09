# BMS Database

面向浙江大学基础医学本科生的课程资料与学习经验网站。

- 网站：[BMS Database](https://bms-zju.github.io/BMS_Database/)
- 内容：课程考核、学习方法、讨论课与考试资料、往届经验
- 构建：MkDocs Material

## 本地预览

使用 Python 3.12 创建独立环境。Windows 可以运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m mkdocs serve
```

提交前建议运行严格构建：

```powershell
.\.venv\Scripts\python.exe -m mkdocs build --strict
```

课程事实应以课程组通知、课件和原始作业要求为依据；无法确认的内容不得猜测，正式页面省略，核查事项留在维护记录。具体维护方式见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [COURSE_HOMEPAGE_GUIDE.md](COURSE_HOMEPAGE_GUIDE.md)。

调整字体、字号、标题层级或阅读样式切换时，参见 [阅读体验维护指南](READING_EXPERIENCE_GUIDE.md)。

小测与单独安排考试按本次时间标注“本学年秋一周周一”等校历起点；具体范围、合集展示及日期周次计算，参见 [学期与校历参考](EXAM_SEMESTER_REFERENCE.md#校历与周次)。
