---
title: 2025-2026 学年夏学期（25级）医学科学素养Ⅱ小测
hide:
  - toc
---

# 2025-2026 学年夏学期（25级）医学科学素养Ⅱ小测 {#2025-2026-ii}

=== "概率与分布小测"

    <section id="probability-quiz" data-export-title="概率与分布小测" markdown="1">

    ### 概率与分布小测 {#probability-quiz-title .resource-panel-title}

    <!--
    source-attribution
    贡献者：刘皓宇（资料提供）。
    资料性质：2025-2026 学年夏学期、25 级小测原始试题照片。
    整理说明：按三张原照片录入，保留题目与分值；小测次数和日期未能确认。
    来源记录：MSL2-INBOX-20261003。
    -->

    !!! info "资料说明"

        本份小测的次数和日期未能确认。照片中部分文字可能受手机相机 AI 处理影响而模糊、错位或失真，内容可能不可靠，请结合课程材料核对。

    ---

    #### 计算题 {#_1 .exam-section .exam-section--analysis}

    1. Suppose there are $10^8$ normal breast cells and 0 intermediate or malignant breast cells among —-year-old females. The probability that a normal breast cell will mutate to become an intermediate cell is $10^{-7}$ per year.

        !!! info "照片辨识"

            起始年龄无法从照片中确认，真实数字可能是附近的“20”。

        1. (6 points) What is the probability that there will be at least 5 intermediate cells by age 21?

        2. What is the expected number of intermediate cells by age 45?

        3. (8 points) The probability that an intermediate cell will mutate to become a malignant cell is $5 \times 10^{-7}$ per year. Suppose a woman has 300 intermediate cells by age 45. What is the probability that she develops breast cancer by age 46?

    2. An experiment is designed to test the potency of a drug on 20 rats. Previous animal studies have shown that a 10-mg dose of the drug is lethal 5% of the time within the first 4 hours; of the animals alive at 4 hours, 10% will die in the next 4 hours.

        1. (8 points) What is the probability that 3 or more rats will die in the first 4 hours?

        2. (8 points) Suppose 2 rats die in the first 4 hours. What is the probability that 2 or fewer rats will die in the next 4 hours?

        3. (8 points) What is the probability that 0 rats will die in the 8-hour period?

        4. (10 points) What is the probability that 1 rat will die in the 8-hour period?

    3. An important issue in assessing nuclear energy is whether excess disease risks exist in the communities surrounding nuclear-power plants. A study undertaken in the community surrounding Hanford, Washington, looked at the prevalence of selected congenital malformations in the counties surrounding the nuclear-test facility.

        1. (8 points) Suppose 27 cases of Down's syndrome are found and only 19 are expected based on Birth Defects Monitoring Program prevalence estimates in the states of Washington, Idaho, and Oregon. Are there significant excess cases in the area around the nuclear-power plant?

        2. (8 points) If the distribution be approximated by a normal distribution, what's the probability of observing 27 cases?

        3. (8 points) Suppose 12 cases of cleft palate are observed, whereas only 7 are expected based on Birth Defects Monitoring Program estimates. What is the probability of observing exactly 12 cases of cleft palate if there is no excess risk of cleft palate in the study area?

    4. Serum cholesterol is an important risk factor for coronary disease. We can show that serum cholesterol is approximately normally distributed, with mean = 219 mg/dL and standard deviation = 50 mg/dL.

        1. (8 points) If the clinically desirable range for cholesterol is < 200 mg/dL, what proportion of people have clinically desirable levels of cholesterol?

        2. (8 points) Some investigators believe that only cholesterol levels over 250 mg/dL indicate a high-enough risk for heart disease to warrant —. What proportion of the population does this group represent?

            !!! info "照片辨识"

                照片中此处文字失真，原词无法确认。

        3. (8 points) What proportion of the general population has borderline high-cholesterol levels—that is, > 200 but < 250 mg/dL?

    </section>

=== "Quiz 1：配对 t 检验答案"

    <section id="quiz-1" data-export-title="Quiz 1：配对 t 检验答案" markdown="1">

    ### Quiz 1：配对 t 检验答案 {#quiz-1-title .resource-panel-title}

    <!--
    source-attribution
    贡献者：汪嘉琪（资料提供）。
    资料性质：2025-2026 学年夏学期（25级）随附答案、评分说明、数据表与 R 脚本。
    整理说明：未附原始题干；保留随附答案，不推定其编写者或作答日期。
    来源记录：MSL2-SUMMER-SUPPLEMENT-20261008。
    -->

    原始题干未提供；以下保留随附数据、答案与评分说明。

    #### 数据

    $d_i = \text{baseline SBP}_i - \text{week 8 SBP}_i$

    | Patient | Baseline SBP | Week 8 SBP | Difference $d_i$ |
    | --- | --- | --- | --- |
    | 1 | 148 | 143 | 5 |
    | 2 | 152 | 153 | -1 |
    | 3 | 141 | 138 | 3 |
    | 4 | 160 | 158 | 2 |
    | 5 | 155 | 151 | 4 |
    | 6 | 149 | 149 | 0 |
    | 7 | 146 | 143 | 3 |
    | 8 | 158 | 160 | -2 |
    | 9 | 150 | 146 | 4 |
    | 10 | 162 | 161 | 1 |
    | 11 | 144 | 142 | 2 |
    | 12 | 156 | 151 | 5 |

    <details class="quiz-answer" markdown="1">
    <summary>查看答案与评分说明</summary>

    Two-sided（5 分）paired t-test（5 分）

    **Step 1. State the hypotheses**

    Let the population mean paired difference be the mean baseline-minus-week-8 difference.

    Because we ask whether blood pressure changed in either direction, this is a two-sided test.

    $H_0:\mu_d=0$（10 分）

    $H_1:\mu_d\ne0$（10 分）

    **Step 2. Calculate the sample mean difference**

    $\bar d=2.1667$（5 分）

    The average observed reduction is about 2.17 mmHg.

    **Step 3. Calculate the sample standard deviation of the paired differences**

    Formula:

    $$s_d=\sqrt{\frac{\sum(d_i-\bar d)^2}{n-1}}$$

    （$s_d$ 公式 5 分）

    For these differences:

    $$\sum(d_i-\bar d)^2=57.6667$$

    Calculation:

    $$s_d=\sqrt{\frac{57.6667}{11}}=2.2896$$

    （$s_d$ 结果 5 分，过程正确则允许 3% 误差）

    **Step 4. Calculate the standard error**

    $$SE(\bar d)=\frac{s_d}{\sqrt n}=\frac{2.2896}{\sqrt{12}}=0.6610$$

    **Step 5. Calculate the t statistic**

    Formula & Calculation:

    $$t=\frac{\bar d-0}{SE(\bar d)}\quad\text{或}\quad\frac{\bar d-0}{s_d/\sqrt n}=\frac{2.1667}{0.6610}=3.2781$$

    （$t$ 公式 5 分，公式中“−0”忽略不扣分；$t$ 结果 5 分。计算过程正确的情况下结果允许 3% 误差。计算过程错误但结果正确不得分）

    Degrees of freedom:

    $$df=n-1=12-1=11$$

    （自由度 10 分，数值正确即得分，不写 $n-1$ 不扣分）

    **Step 6. Find the critical t statistic**

    For a two-sided paired t-test:

    $t=2.201$（查表 $t$ 值 5 分，不允许四舍五入，不允许误差）

    **Step 7. Conclusion**

    Because:

    $t(\mathrm{calc})>t(\mathrm{critical});\ p<0.05$（比较过程 5 分）

    we reject the null hypothesis.（结论 5 分）

    There is statistically significant evidence that mean systolic blood pressure changed after the 8-week lifestyle intervention. Since the observed mean difference is positive, the sample suggests an average decrease in systolic blood pressure.

    **99% CI calculation:**

    $$CI=\bar d\pm t_{1-\alpha/2,\ n-1}\cdot\frac{s_d}{\sqrt n}$$

    （公式 10 分）

    $T=3.106$（5 分，不允许四舍五入，不允许误差）

    $$SE=\frac{s_d}{\sqrt n}=\frac{2.290}{\sqrt{12}}=0.661$$

    The margin of error is:

    $$\text{Margin of error}=t_{\mathrm{critical}}\cdot SE=3.106\cdot0.661=2.053$$

    $$CI=2.167\pm2.053=(0.114,\ 4.219)\ \mathrm{mmHg}$$

    （计算结果 5 分，过程正确则允许 3% 误差）

    </details>


    <details class="quiz-answer" markdown="1">
    <summary>查看随附 R 代码</summary>

    ~~~r
    # -----------------------------
    # Data
    # -----------------------------

    baseline <- c(148, 152, 141, 160, 155, 149, 146, 158, 150, 162, 144, 156)
    week8    <- c(143, 153, 138, 158, 151, 149, 143, 160, 146, 161, 142, 151)

    # Define paired difference
    # Here: d = baseline - week8
    # Positive values mean SBP decreased after intervention

    d <- baseline - week8
    d

    # -----------------------------
    # Paired two-sided t-test
    # -----------------------------

    t.test(
      x = baseline,
      y = week8,
      paired = TRUE,
      alternative = "two.sided",
      conf.level = 0.99
    )
    ~~~

    </details>

    </section>

=== "Quiz 2：R 编程任务"

    <section id="quiz-2" data-export-title="Quiz 2：R 编程任务" markdown="1">

    ### Quiz 2：R 编程任务 {#quiz-2-title .resource-panel-title}

    <!--
    source-attribution
    贡献者：汪嘉琪（资料提供）。
    资料性质：2025-2026 学年夏学期（25级）R 编程小测任务说明。
    整理说明：未附配套数据与结果答卷；日期依据文件名及测验单元通知。
    来源记录：MSL2-SUMMER-SUPPLEMENT-20261008。
    -->

    > **本学年夏一周周一：** 2026 年 4 月 27 日  
    > **日期：** 2026.06.05  
    > **周次：** 夏第 6 周周五

    本份保留任务说明；配套数据文件和结果答卷未随材料提供。

    ---

    #### 一、数据读取与预处理

    1. **数据获取：**请从钉钉课程群下载数据文件 `data_quiz2_v2-Eng.txt`，并将其设置在你的 R 语言工作目录（Working Directory）中。

    2. **路径要求：**在 R 脚本中读取数据时，请直接使用该文件名称（即相对路径），请勿使用绝对路径（例如 `C:/Users/...`），以确保代码在不同设备上的可复现性。

    3. **样本过滤：**在进行任何统计计算之前，请务必从数据集中识别并剔除你本人的数据记录，仅保留班级其余同学的样本。

    #### 二、统计检验与计算

    针对上述清洗后的数据集，请检验班级除自己外的其余同学在 `round2` 的得分是否显著高于 `round1` 的得分（$\alpha=0.01$），并计算差异的 99% 置信区间（99% CI）。

    为了对比不同假设前提下的检验效能，请分别使用以下三种方法完成计算，并对每段代码具体对应哪种统计方法进行注释：

    - **方法 A：**配对样本 $t$ 检验（Paired t-test）
    - **方法 B：**假设方差齐性的独立双样本 $t$ 检验（Pooled 2-sample t-test）
    - **方法 C：**不假设方差齐性的独立双样本 $t$ 检验（Welch t-test）

    #### 三、结果填报

    请提取上述三种方法的计算结果，并将各自对应的统计量准确填入答卷的相应位置。

    #### 四、代码汇总与提交规范

    1. **提交方式：**请将本人完成的 R 代码粘贴至钉钉群共享文档 `R-script.txt` 中本人姓名和学号信息的下方，请勿修改他人的代码或姓名学号信息。该文档将作为完整脚本统一运行；若某位同学提交的代码段导致运行报错，将扣除该同学相应分数。

    2. **独立完成：请勿使用任何 AI 工具生成代码。** 本次练习旨在考察真实的独立分析与 R 编程能力，一经发现代码为 AI 生成，本次练习将按零分计算。

    汇总代码格式展示：

    ~~~r
    # ==== 张三 学号1234567 =====
    # paired t-test:
    abc <- read.table(....)
    edf <- t.test(...)

    # pooled t-test:
    abc <- read.table(....)
    edf <- t.test(...)

    # Welch's t-test:
    abc <- read.table(....)
    edf <- t.test(...)

    # ==== 李四 学号2345668 =====
    # paired t-test:
    abc <- read.table(....)
    edf <- t.test(...)

    # pooled t-test:
    abc <- read.table(....)
    edf <- t.test(...)

    # Welch's t-test:
    abc <- read.table(....)
    edf <- t.test(...)
    ~~~

    </section>

=== "Quiz 3：卡方检验答案"

    <section id="quiz-3" data-export-title="Quiz 3：卡方检验答案" markdown="1">

    ### Quiz 3：卡方检验答案 {#quiz-3-title .resource-panel-title}

    <!--
    source-attribution
    贡献者：汪嘉琪（资料提供）。
    资料性质：2025-2026 学年夏学期（25级）随附答案与评分标准。
    整理说明：日期依据卡方检验单元通知；保留原件分值及其不一致处，不推定答案编写者。
    来源记录：MSL2-SUMMER-SUPPLEMENT-20261008。
    -->

    > **本学年夏一周周一：** 2026 年 4 月 27 日  
    > **日期：** 2026.06.08  
    > **周次：** 夏第 7 周周一

    本份为答案与评分标准，保留原文件中的已知条件。

    **总评分原则：**公式分、过程分、结果分分开给。$\chi^2$ 数值、p 值/临界值比较和最终结论，必须有对应的正确公式与计算过程支持；仅写最终答案不计结果分。

    **数值要求：**计算结果至少保留两位小数；过程正确时允许约 3% 误差。

    ---

    #### 第 1 题：χ² 拟合优度检验（共 50 分） {.exam-section .exam-section--analysis data-toc-label="第 1 题：χ² 拟合优度检验"}

    已知：$O_{\text{女}}=23$，$O_{\text{男}}=17$，$n=40$；理论比例男∶女 = 1.77∶1；$\alpha=0.01$。

    <details class="quiz-answer" markdown="1">
    <summary>查看答案与评分标准</summary>

    **步骤 1　检验类型与假设（10 分）**

    $H_0$：本班性别构成符合男∶女 = 1.77∶1。（5 分）

    $H_1$：本班性别构成偏离该理论比例。（5 分）

    **步骤 2　理论比例与期望数（10 分）**

    比例公式：$p_{\text{男}}=1.77/(1.77+1)$（2 分）$=0.64$（2 分），$p_{\text{女}}=1/(1.77+1)$（2 分）$=0.36$（2 分）。

    期望数公式：$E_i=n\times p_i$。（公式 2 分）

    $E_{\text{男}}=25.56$，$E_{\text{女}}=14.44$。（计算 4 分）

    若把男∶女比例反用，本步及后续 $\chi^2$ 结果不得分。

    !!! info "原文件分值"

        本步骤标题标为 10 分，各分项标注合计为 14 分，保留原文件标注。

    **步骤 3　χ² 统计量（12 分）**

    公式：$\chi^2=\sum[(O_i-E_i)^2/E_i]$。（公式 4 分）

    过程：男：$(17-25.56)^2/25.56=2.87$；女：$(23-14.44)^2/14.44=5.07$。（过程 4 分）

    结果：$\chi^2=7.94$。（结果 4 分）

    **步骤 4　自由度与参考值（10 分）**

    自由度公式：$df=k-1=1$。（自由度 5 分）

    临界值 $\chi^2(0.01,df=1)=6.64$。（5 分）

    **步骤 5　比较与结论（8 分）**

    比较：$7.94>6.64$，$p<0.01$。（4 分）

    结论：拒绝 $H_0$；本班性别构成显著偏离理论比例，女生多于期望、男生少于期望。（4 分）

    </details>

    #### 第 2 题：2×2 列联表 χ² 独立性检验（共 50 分） {.exam-section .exam-section--analysis data-toc-label="第 2 题：2×2 列联表 χ² 独立性检验"}

    已知：$n=180$；好依从性 100 人（控制 78，未控制 22）；差依从性 80 人（控制 48，未控制 32）；$\alpha=0.05$。

    <details class="quiz-answer" markdown="1">
    <summary>查看答案与评分标准</summary>

    **观察值与期望值（括号内为 E）**

    | 用药依从性 | 血压控制 | 血压未控制 | 行合计 |
    | --- | --- | --- | --- |
    | 好 | 78（E=70） | 22（E=30） | 100 |
    | 差 | 48（E=56） | 32（E=24） | 80 |
    | 列合计 | 126 | 54 | 180 |

    **步骤 1　检验类型、表格与假设（10 分）**

    $H_0$：用药依从性与血压控制相互独立/无关联。（5 分）

    $H_1$：用药依从性与血压控制有关联。（5 分）

    **步骤 2　期望数（12 分）**

    公式：$E_{ij}=(\text{行合计}\times\text{列合计})/\text{总例数}$。（公式 4 分）

    计算：$E_{\text{好,控制}}=100\times126/180=70$；$E_{\text{好,未控制}}=100\times54/180=30$；$E_{\text{差,控制}}=80\times126/180=56$；$E_{\text{差,未控制}}=80\times54/180=24$。（计算 8 分）

    **步骤 3　χ² 统计量（12 分）**

    公式：$\chi^2=\sum[(O-E)^2/E]$。（公式 4 分）

    过程：$(78-70)^2/70=0.91$；$(22-30)^2/30=2.13$；$(48-56)^2/56=1.14$；$(32-24)^2/24=2.67$。（过程 4 分）

    结果：$\chi^2=6.86$。（结果 4 分）

    **步骤 4　自由度与参考值（8 分）**

    自由度公式：$df=(r-1)(c-1)$（公式 2 分）；$df=1$（结果 2 分）。

    临界值 $\chi^2(0.05,df=1)=3.84$。（4 分）

    **步骤 5　比较与结论（8 分）**

    比较：$6.86>3.84$，或 $p<0.05$。（4 分）

    结论：拒绝 $H_0$；用药依从性与血压控制状态有统计学关联。（4 分）

    </details>

    </section>

=== "Quiz 4：回归与相关"

    <section id="quiz-4" data-export-title="Quiz 4：回归与相关" markdown="1">

    ### Quiz 4：回归与相关 {#quiz-4-title .resource-panel-title}

    <!--
    source-attribution
    贡献者：汪嘉琪（资料提供）。
    资料性质：2025-2026 学年夏学期（25级）回归与相关小测原始试题。
    整理说明：日期按文档标题；原件未附答案。
    来源记录：MSL2-SUMMER-SUPPLEMENT-20261008。
    -->

    > **本学年夏一周周一：** 2026 年 4 月 27 日  
    > **日期：** 2026.06.12  
    > **周次：** 夏第 7 周周五

    填空：如无特殊说明，除不尽时保留至少两位小数；除自由度、查表值、p 值范围外，计算结果允许 3% 以内误差。

    ---

    #### 填空题（共 100 分） {.exam-section .exam-section--short data-toc-label="填空题"}

    A pharmacology researcher studies the relationship between drug dose and response score in 5 patients.

    $x$ = dose: 1, 2, 3, 4, 5

    $y$ = response score: 52, 55, 61, 64, 68

    For the simple linear regression line $y=bx+a$:

    $b$ = \_\_\_\_（10 分），$a$ = \_\_\_\_（10 分）

    We want to use F-ratio to test the significance of this regression line.

    $H_0$: \_\_\_\_\_\_\_\_\_\_\_\_（10 分）

    $H_1$: \_\_\_\_\_\_\_\_\_\_\_\_（10 分）

    Regression sum of squares (SS) = \_\_\_\_\_\_\_\_（5 分）

    Residual SS = \_\_\_\_\_\_\_\_（5 分）

    Df1 = \_\_\_\_（5 分）；Df2 = \_\_\_\_（5 分）

    Regression mean of squares (MS) = \_\_\_\_\_\_\_\_（5 分）

    Residual MS = \_\_\_\_\_\_\_\_（5 分）

    F(calculated) = \_\_\_\_（5 分）；F(critical) = \_\_\_\_（5 分）

    Based on the F table, the p-value range is \_\_\_\_\_\_\_\_（5 分）

    When alpha = 0.05, your conclusion is: \_\_\_\_\_\_\_\_（5 分）

    Pearson correlation coefficient = \_\_\_\_\_\_\_\_（5 分，保留四位小数）

    Correlation of determination = \_\_\_\_%（5 分）

    </section>

=== "补测"

    <section id="makeup-quiz" data-export-title="补测" markdown="1">

    ### 补测 {#makeup-quiz-title .resource-panel-title}

    <!--
    source-attribution
    贡献者：汪嘉琪（资料提供）。
    资料性质：2025-2026 学年夏学期（25级）补测试卷。
    整理说明：日期按卷首 2026-06-15，非文件名日期；原件未附答案。
    来源记录：MSL2-SUMMER-SUPPLEMENT-20261008。
    -->

    > **本学年夏一周周一：** 2026 年 4 月 27 日  
    > **日期：** 2026.06.15  
    > **周次：** 夏第 8 周周一

    ---

    #### 选择题 {.exam-section .exam-section--choice}

    1. A cross-sectional study compares mean C-reactive protein (CRP, mg/L) between two unrelated groups: patients with disease A (n = 18, mean = 9.6, SD = 7.8) and healthy controls (n = 42, mean = 5.1, SD = 3.2). The two groups contain different people, and equal variances are not scientifically justified. Which analysis choice is most defensible?

        **A.** Paired t-test, because two groups are being compared.  
        **B.** Pooled two-sample t-test, because the sample sizes are unequal.  
        **C.** Welch two-sample t-test, because the groups are independent and unequal variances are plausible.  
        **D.** Chi-square test, because disease status is categorical.

    2. A study compares systolic blood pressure (SBP) between oral contraceptive users and non-users. The groups are independent. R gives the following output:

        ~~~text
        Welch Two Sample t-test
        
        t = 0.81, df = 15.0, p-value = 0.43
        95 percent confidence interval:
         -8.91  19.75
        sample estimates:
        mean in OC users      mean in non-users
        132.86                127.44
        ~~~

        Which conclusion is most defensible?

        **A.** OC use significantly increases SBP because 132.86 is larger than 127.44.  
        **B.** The null hypothesis is proven true because p > 0.05.  
        **C.** The sample mean is higher among OC users, but the evidence is not statistically significant and the confidence interval is wide.  
        **D.** The two groups must have equal population means because the confidence interval contains zero.

    3. Before collecting data, investigators state a one-sided hypothesis that carbon monoxide exposure reduces time to angina onset compared with normal air. The two groups are independent and equal variances were judged reasonable. The pooled t-test gives t = -3.04 with df = 61; the left-tail p-value is between 0.005 and 0.001. Which statement is best?

        **A.** There is evidence that carbon monoxide reduces time to angina onset, provided the one-sided direction was specified before seeing the data.  
        **B.** The result is not significant because the t statistic is negative.  
        **C.** A two-sided conclusion must be reported because one-sided t-tests are never allowed.  
        **D.** The result proves that carbon monoxide causes angina in every exposed patient.

    4. A migraine study randomly assigns 27 independent volunteers to Drug A, Drug B, or Drug C, with 9 per group. Pain is measured on a 1 to 10 scale. R gives:

        ~~~text
        summary(aov(pain ~ drug))
                    Df Sum Sq Mean Sq F value   Pr(>F)
        drug         2  28.22  14.111   11.91 0.000256
        Residuals   24  28.44   1.185
        ~~~

        Which conclusion is most justified at alpha = 0.05?

        **A.** All three drug means are significantly different from each other.  
        **B.** At least one population mean pain score differs.  
        **C.** Drug A is definitely better than Drug B because the ANOVA p-value is small.  
        **D.** The result proves that the pain scores are normally distributed.

    5. An ANOVA table for four independent treatment groups is partially shown below:

        ~~~text
        Source       df    Sum Sq
        Treatment     3      96
        Residual     20     160
        Total        23     256
        ~~~

        Which F statistic should be used for the one-way ANOVA test?

        **A.** F = 96 / 160 = 0.60  
        **B.** F = 160 / 96 = 1.67  
        **C.** F = (96 / 3) / (160 / 20) = 4.00  
        **D.** F = 256 / 23 = 11.13

    6. A nutrition study measures the same 8 patients after each of three diets: low-fat, Mediterranean, and low-carbohydrate. A student runs ordinary one-way ANOVA treating the 24 measurements as if they came from 24 unrelated people. Which assumption is most directly violated?

        **A.** The observations are independent within and between groups.  
        **B.** The outcome variable is quantitative.  
        **C.** The group variable has more than two levels.  
        **D.** The ANOVA F statistic is right-tailed.

    7. R output for a table of exposure group (low, medium, high) by disease status (yes, no) is shown below:

        ~~~text
        Pearson's Chi-squared test
        
        X-squared = 12.4, df = 2, p-value = 0.0020
        ~~~

        Which interpretation is best?

        **A.** There is evidence of association between exposure group and disease status, but this output alone does not prove causation.  
        **B.** The mean disease status differs across the three exposure groups.  
        **C.** The exposure variable is normally distributed.  
        **D.** The p-value tells us that 0.2% of participants were diseased.

    8. A pilot study compares recovery between a new therapy and control:

        ~~~text
                         Recovered   Not recovered
        New therapy          1             9
        Control              6             4
        ~~~

        The expected count for each group-by-recovery cell involving "Recovered" is 3.5. Which statement is best?

        **A.** Pearson's chi-square approximation may be unreliable; Fisher's exact test or a justified redesign/combination strategy should be considered.  
        **B.** The chi-square test is invalid because the observed table is 2 x 2.  
        **C.** A paired t-test should be used because each row has two columns.  
        **D.** The p-value must be exactly zero because one observed cell is small.

    9. A simple regression is fitted using depression as the outcome and weight as the predictor. R gives:

        ~~~text
        Coefficients:
                     Estimate Std. Error t value Pr(>|t|)
        (Intercept)  -2.0871    4.7543   -0.439   0.67227
        weight        2.6667    0.7002    3.808   0.00518
        
        Multiple R-squared: 0.6445
        F-statistic: 14.5 on 1 and 8 DF, p-value: 0.005175
        ~~~

        Which number directly tests whether weight has a nonzero linear association with depression in this model?

        **A.** The intercept p-value, 0.67227.  
        **B.** The slope p-value for weight, 0.00518, equivalently the model F-test p-value in simple regression.  
        **C.** The residual standard error, because it is measured in depression units.  
        **D.** The R-squared value, because it is the p-value for the model.

    10. A simple linear regression of kidney filtration rate on age reports R-squared = 0.64 and slope p < 0.001. Which statement is most accurate?

        **A.** Age explains about 64% of the sample variability in kidney filtration rate under this fitted linear model, but the result alone does not prove causation.  
        **B.** Exactly 64% of patients have kidney disease caused by age.  
        **C.** The p-value is unnecessary because R-squared is always a probability.  
        **D.** A high R-squared proves that the residual assumptions are satisfied.

    </section>
