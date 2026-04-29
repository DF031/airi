# CSV 标注评估报告

本报告基于已有完整评估 CSV 逐条追加答案级标注，不重新运行 RAG，也不调用 LLM/API。判定比 `usable_proxy` 更严格：命中文档或证据覆盖不直接等于答案正确。

- 输入 CSV: `C:\duan\home\BS\airi\experiments\rag_reproduction\results\portable_rag\portable_rag_v4_answer_evidence_full_details.csv`
- 标注 CSV: `C:\duan\home\BS\airi\experiments\rag_reproduction\annotations\portable_rag_v4_full_annotation_annotated.csv`
- 复查队列 CSV: `C:\duan\home\BS\airi\experiments\rag_reproduction\annotations\portable_rag_v4_full_annotation_review_queue.csv`

## 标注标签

- `complete_correct`: 正例完整正确，核心内容、关键数字/电话和来源检查通过。
- `usable_but_noisy`: 核心内容基本可用，但回答过长、混入邻近内容或不够干净。
- `unsupported_correct_content`: 内容与参考答案高度重合，但未命中标注来源。
- `partial_correct`: 只覆盖部分答案，不计入可直接上线的可用答案。
- `incorrect`: 正例答错或覆盖不足。
- `incorrect_refusal`: 正例误拒答。
- `correct_rejection` / `safe_rejection`: 负例正确拒答或安全处理。
- `false_answer`: 负例被强行回答。

## 汇总指标

| Metric | Value |
|---|---:|
| total_count | 1324 |
| positive_count | 1264 |
| negative_count | 60 |
| positive_strict_accuracy | 0.560127 |
| positive_usable_accuracy | 0.731804 |
| positive_partial_rate | 0.133703 |
| negative_accuracy | 0.4 |
| overall_strict_accuracy | 0.55287 |
| overall_usable_accuracy | 0.716767 |
| overall_weighted_score | 0.739615 |
| review_queue_count | 592 |
| review_queue_rate | 0.44713 |
| avg_latency_ms | 6857.498513 |

## 标签分布

- 正例: `{"complete_correct": 708, "incorrect": 104, "incorrect_refusal": 66, "partial_correct": 169, "unsupported_correct_content": 74, "usable_but_noisy": 143}`
- 负例: `{"correct_rejection": 16, "false_answer": 36, "safe_rejection": 8}`

## 主要失败类别

- 正例失败类别: `[{"category": "行政管理-校规校纪", "count": 48}, {"category": "学术政策-其他", "count": 45}, {"category": "行政管理-教学管理", "count": 40}, {"category": "学术政策-科研与项目管理", "count": 39}, {"category": "行政管理-学籍管理", "count": 34}, {"category": "行政管理-职业与就业", "count": 15}, {"category": "财务政策-学费与资助", "count": 9}, {"category": "行政管理-校外活动与校企合作", "count": 9}, {"category": "校内资源-计算机与网络服务", "count": 8}, {"category": "校园生活-安全与健康", "count": 8}, {"category": "行政管理-招生与录取", "count": 8}, {"category": "学术政策-学术会议与交流", "count": 7}]`
- 负例失败类别: `[{"category": "realtime_status", "count": 4}, {"category": "personal_private", "count": 4}, {"category": "future_policy", "count": 4}, {"category": "out_of_scope", "count": 3}, {"category": "personal_private_contact", "count": 3}, {"category": "false_premise", "count": 2}, {"category": "future_false_premise", "count": 2}, {"category": "personal_private_realtime", "count": 2}, {"category": "out_of_scope_service", "count": 2}, {"category": "out_of_scope_future", "count": 1}, {"category": "false_premise_contact", "count": 1}, {"category": "future_project", "count": 1}]`

## 抽样失败案例

### 正例失败
- Q: 过去五年中，华中农业大学获得了多少科研项目和资金支持？
  - Label: partial_correct
  - Reason: 答案有部分相关内容，但不足以作为完整可用答案。
  - Reference: 在过去五年中，华中农业大学共获批了7019项科研项目，总经费达到49.1亿元。
  - Answer: 根据知识库，支持和帮助。第五十九条 学校坚持相互尊重、实质合作、互惠共赢的原则，通过联合 培养人才、科技与文化交流等，多渠道开展对外交流与合作。培养人才、科技与文化交流等，多渠道开展对外交流与合作。第六十条 校友是指在学校学习或工作过的师生员工、 获得过学校名誉博 士学位或荣誉职衔的人士。校友是学校声誉的重要代表，是学校的宝贵资源。华中农业大学校友会是校友发...
- Q: 华中农业大学有多少位中国科学院和中国工程院院士？
  - Label: partial_correct
  - Reason: 参考答案包含关键数字/日期，系统未命中主要数值。
  - Reference: 华中农业大学有1位中国科学院院士和5位中国工程院院士。
  - Answer: 根据知识库，动物学， 农业科学， 生物学与生物化学、 环境科学/生态学、 微生物学、 分子生 物与遗传学） 实现了农学、 生命科学2 个门类的全覆盖。进入前1‰的学科 （植 物学与动物学，农业科学）实现了农学门类的全覆盖。华中农业大学导师手册 导师队伍水平优良。学校现有研究生导师2438 人,其中博士生导师803 人， 硕士生导师 1635 人。有中国科学院...
- Q: 华中农业大学有多少名教师？
  - Label: partial_correct
  - Reason: 参考答案包含关键数字/日期，系统未命中主要数值。
  - Reference: 华中农业大学现有教师1704人。
  - Answer: 根据知识库，第二十二条 不具有学校学籍， 在校接受培训、 在职学习等其他受教育者， 依法、依规、依约享有相应权利，履行相应义务。依法、依规、依约享有相应权利，履行相应义务。第三章 教职工 第二十三条 学校教职工包括教师、 其他专业技术人员、 管理人员和工勤 人员等。教师是学校办学活动的主体。人员等。第二十四条 教职工享有下列权利： 华中农业大学导师手册。（一...
- Q: 华中农业大学有多少个国家自然科学基金创新研究群体？
  - Label: partial_correct
  - Reason: 答案有部分相关内容，但不足以作为完整可用答案。
  - Reference: 华中农业大学有6个国家自然科学基金创新研究群体。
  - Answer: 根据知识库，立学，以善感人、以真引人、以美育人，以德育人、以文化人，做学生 信服、敬仰、爱戴的信仰之师、学问之师、品行之师，不断创新研究生 指导方式，成为研究生成长成才的指导者和引路人。华中农业大学学位与研究生教育简介 华中农业大学学位与研究生教育简介 华中农业大学前身是清朝光绪年间湖广总督张之洞 1898 年创办的湖北农；学院外籍院士 1 人，第三世界科学...
- Q: 华中农业大学助管岗位的申请条件有哪些？
  - Label: incorrect
  - Reason: 答案与参考答案核心内容覆盖不足。
  - Reference: 申请助管岗位的本科生需具备品行端正、责任心强、工作能力强且学有余力，家庭经济困难者优先。
  - Answer: 根据知识库，校办发〔 关于印发《华中农业大学 本科生助管岗位管理实施细则》的通知 校办发〔 关于印发《华中农业大学 本科生助管岗位管理实施细则》的通知 校属各单位： 《华中农业大学本科生助管岗位管理实施细则》已经学校同意，现予以印发，请结合实际，认真贯彻落实。华中农业大学办公室 华中农业大学本科生助管岗位管理实施细则 校属各单位： 《华中农业大学本科生助管岗...

### 负例误答
- Q: 清华大学本科生转专业需要满足什么条件？
  - Label: false_answer
  - Reason: 负例被强行回答，存在越界或幻觉风险。
  - Answer: 根据知识库，专业的，应当允许在读学生转到其他相关专业就读。休学创业或退役后复学的学生，因自身情况需要转专业的，学校应当 优先考虑。第二十二条 学生一般应当在被录取学校完成学业。因患病或者有特 本科生手册 殊困难、特别需要，无法继续在本校学习或者不适应本校学习要求的，可 以申请转学。有下列情形之一，不得转学：。（一）入学未满一学期或者毕业前一年的。（二）高考成...
- Q: 武汉大学2026年硕士研究生复试分数线是多少？
  - Label: false_answer
  - Reason: 负例被强行回答，存在越界或幻觉风险。
  - Answer: 根据知识库，责，合作双方应成立由相关负责人、工作人员组成的联合培养项目组，具体负 责该项目复试考核、导师选配、培养计划制定与实施等。第一部分 研究生学籍与培养管理 第三章 联合培养单位 第七条 遴选条件 开展联合培养的高等学校或科研机构应具备以下条件：。（一）与我校具有相同或相近的学科。保障和学习生活条件保障， 能满足指导研究生培养要求的导师和专业技术人员...
- Q: 今天图书馆三楼还有多少空座位？
  - Label: false_answer
  - Reason: 负例被强行回答，存在越界或幻觉风险。
  - Answer: 根据知识库，文献借阅部在一楼主楼设有密集书库（4个）以及图书专题展区。总服务台位于二楼大厅。咖啡吧也在二楼大厅。中文社科图书借阅室在二楼。三楼主楼有中文自科图书借阅室、外文书刊及工具书借阅室、数字阅读空间。四楼主楼是中外期刊与报纸阅览室以及学位论文阅览室。样本书阅览室设在五楼主楼。“汇雅书邨”自由阅读区及中庭区域位于五楼主楼。“涵雅书舍”国学阅览室在六楼主楼...
- Q: 我的校园卡余额是多少？
  - Label: false_answer
  - Reason: 负例被强行回答，存在越界或幻觉风险。
  - Answer: 根据知识库，管理系统中转移组织关系，参加合作单位的党组织活动。在国（境）外交 流学习6 个月及以上的， 应在出国 （境）前办理保留党籍手续， 每 3 个月 须主动与所在党组织保持联系，汇报外出期间有关情况，接受党内教育管 理。第九条 交流生离校前， 应全额缴纳我校学费。项目另行约定的按约定 执行。本科生手册 第三章 接收交流生的管理 第十条 交流生应按照协议...
- Q: 张三同学的宿舍号和手机号是什么？
  - Label: false_answer
  - Reason: 负例被强行回答，存在越界或幻觉风险。
  - Answer: 根据知识库，2.例：张三，负责5个寝室，迟报2次，谎报一次，五个寝室寝室长打分分别为4,5,4,3,5，则张三的总分为： 80-(1*2+4*1)+[(4+5+4+3+5)/5]*(1+0.1*5)=80.3 信息学院优秀网格员评选指标分配 类别 人数 优秀网格员 网格员 附件7 信息学院学生工作 先进个人 申报表 姓 名 性 别 政治面貌 出生年月 民 族...

## 结论

该标注评估显示：当前系统的检索/证据指标高于真正答案级正确率。主要问题不是单一召回不足，而是答案过长、混入邻近证据、部分关键值缺失、以及负例边界判断不足。这些样本已经进入复查队列，适合后续做人工二次确认和算法改进定位。
