# 项目展示文案

分类：**Workflow Connector / Experimental Integration**（工作流连接器 / 实验性集成）。

## 可直接使用的介绍

**Visual Pipeline Connector** 将 QQ 群中的明确绘图指令连接到管理员配置的图像 API，提供群来源授权、单任务执行、请求去重、超时和图片响应校验。项目适合探索消息平台中的文字生成图片工作流，使用者自备授权服务与密钥。

English: Visual Pipeline Connector is an experimental AstrBot plugin that connects explicit image-generation commands in authorized QQ groups to an operator-configured Images API. It includes scoped access, single-job execution, in-memory deduplication, request timeouts and bounded image validation.

成熟度说明：v0.1.0 发布候选；通过真实 AstrBot SDK 与假上游的离线测试，真实图像服务与 QQ 端到端联调尚待部署者完成。

## 展示时应保留的区别

这是应用集成项目，不能据此宣称自研图像基础模型、正式平台认证、商业部署规模、Google Cloud/腾讯云实际部署或已通过创业扶持审核。性能、活跃用户、客户、团队与外部部署必须有对应证据才能列入网站。SDK、依赖和平台属于各自维护方。

不要把名称替换当作风险消除：如果未来加入其他图像接口、登录方式或图片输入，应同步审查真实接口授权、数据流与内容规则。不要把旧私有桥接能力写成此发布候选的现有功能。
