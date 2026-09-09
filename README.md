# BMS Database

面向浙江大学基础医学本科生的课程资料与学习经验网站。

- 网站：[BMS Database](https://bms-zju.github.io/BMS_Database/)
- 内容：课程考核、学习方法、讨论课与考试资料、往届经验
- 构建：MkDocs Material

## 资料使用规范

本站资料免费供学习参考，欢迎分享本站页面链接。

- 使用时保留原有署名、来源链接和使用说明。
- 未经相关权利人许可，不得转载全文或重新上传文件；将完整资料转成图片、扫描件或其他文件后再发布，同样适用。
- 禁止将资料用于付费题库、出售资料包、收费课程配套材料等商业用途，本站不提供商业使用授权。
- 个人学习中的保存、笔记和打印，依具体材料的许可与法律规定处理。

具体材料已有有效许可或法律另有规定的，按其适用范围处理；上述说明不变更既有许可，也不扩大本站对第三方内容的授权。

仓库保留 [MIT 许可](LICENSE)。课程资料、字体和图标等如有单独的许可、署名或使用要求，应查看对应说明，不将所有第三方材料视为同一授权范围。完整说明见 [来源与使用范围](https://bms-zju.github.io/BMS_Database/contribute/sources-and-permissions/#resource-use)。

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

## 仓库文件

`docs/` 保存网站页面与公开资源，其他入库文件用于构建和持续维护：

| 文件或目录 | 用途 |
| --- | --- |
| `mkdocs.yml`、`requirements.txt`、`.github/` | 网站配置、固定依赖和构建部署流程 |
| `overrides/`、`hooks/` | 主题模板、自定义图标和构建时的资料说明 |
| `CONTRIBUTING.md`、三份 `*_GUIDE.md` | 贡献、课程主页、回忆卷与阅读体验的维护规则 |
| `COURSE_NAME_MAP.yml`、`EXAM_SEMESTER_REFERENCE.md` | 课程名称、目录、学期和资料归属的核对依据 |
| `ACADEMIC_CALENDAR.json`、`scripts/`、`tests/` | 已核对校历、周次计算和边界测试 |
| `LICENSE`、`.gitignore` | 仓库许可与本地文件忽略规则 |

本地的 `AGENTS.md`、`HANDOFF.md`、`ROADMAP.md`、`.agents/`、`.codex/` 已由 `.gitignore` 排除，不作为共享文件的依赖。本机地址、原始材料、来源登记和过程记录由维护者在仓库外或已忽略的本地入口保存；可共享的规范与脚本使用相对路径。生成站点、虚拟环境和缓存不入库；`.git/` 由 Git 管理，不作为清理对象。
