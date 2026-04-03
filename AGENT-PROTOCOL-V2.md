# Team Office 智能体协作协议 V2

## 概述

V2协议在V1基础上增加**定向消息路由**和**自主响应规则引擎**，让Agent之间能自主处理确定性查询，同时确保变更类操作经过人类审批。

## 参与成员

| 成员ID | 人类名 | 主Agent名 | 职责 |
|--------|--------|----------|------|
| qianyuang | 宇昂 | 研究局局长 | 制作人/总体把控 |
| ameng | A梦 | 小梦 | 前端开发/基础设施 |
| antian | 岸天 | 爱芮 | 功能开发/实现 |
| atlas | — | 拓界 | 首席增长架构师（AI Agent） |

## 数据库连接

```
SUPABASE_URL = https://elnzkemqcmdqefwyldoh.supabase.co
SUPABASE_KEY = sb_publishable_dqOvhjfZLECtQNvcX5JIqg_p8iojSMN
```

## 表结构（V2扩展）

### office_messages（V2新增字段）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| to_member_id | text | NULL | 目标成员ID。NULL=广播，具体值=定向消息 |
| reply_to | uuid | NULL | 回复的消息ID，形成消息线程 |
| auto_flag | text | 'pending' | auto/human/pending/done |
| token_est | int | 0 | 预估消耗token数 |
| priority_level | int | 2 | 1=紧急 2=普通 3=低优 |

### V2新增 msg_type 值

| msg_type | 说明 | auto_flag处理 |
|----------|------|-------------|
| query | 查询型消息（大概率可自动回复） | pending → auto/done |
| auto_reply | Agent自动生成的回复 | done |
| approval | 需要人类审批的请求 | human |

其余表（office_agents/tasks/decisions/config）结构不变，使用方式不变。

## 智能体标准工作流（V2版）

### 会话开始时

```
1. 上报状态
   PATCH office_agents SET status='working' WHERE id='{MY_ID}'

2. 读取定向消息（优先处理）
   GET office_messages?to_member_id=eq.{MY_ID}&auto_flag=eq.pending&order=priority_level.asc,created_at.asc

3. 读取广播消息（最近10条，了解上下文）
   GET office_messages?to_member_id=is.null&order=created_at.desc&limit=10

4. 读取我的任务
   GET office_tasks?owner=eq.{MY_ID}&status=neq.done

5. 读取token预算
   GET office_config?key=eq.token_budget_{MY_ID}

6. 对每条pending消息执行判断链（见下文）
```

### 消息判断链

收到一条 `to_member_id=自己` 且 `auto_flag=pending` 的消息时：

```
Step 1: 是否是查询已确认信息？
  ├─ 查 office_decisions → 有匹配 → AUTO_RESPOND
  ├─ 查 office_tasks → 状态/进度查询 → AUTO_RESPOND
  ├─ 查 office_config key=api_spec_*/table_spec_*/doc_index_* → 有匹配 → AUTO_RESPOND
  └─ 无匹配 → Step 2

Step 2: 预估token消耗
  ├─ < 2000 tokens → 继续 Step 3
  └─ >= 2000 tokens → NEED_HUMAN_APPROVAL

Step 3: 是否涉及变更类操作？
  ├─ 修改已确认方案 → NEED_HUMAN_APPROVAL
  ├─ 新增/删除功能 → NEED_HUMAN_APPROVAL
  ├─ 外部操作（git push/发布/支付）→ NEED_HUMAN_APPROVAL
  └─ 否 → Step 4

Step 4: 内容是否有歧义？
  ├─ 无法从现有文档找到明确答案 → NEED_HUMAN_APPROVAL
  └─ 可明确回答 → AUTO_RESPOND

兜底：NEED_HUMAN_APPROVAL
```

### AUTO_RESPOND 处理

```
a. POST office_messages:
   - msg_type: 'auto_reply'
   - reply_to: 原消息id
   - auto_flag: 'done'
   - content: 回复内容（引用数据来源）

b. PATCH 原消息: auto_flag = 'done'

c. 更新 token_budget: used_today += 实际消耗
```

### NEED_HUMAN_APPROVAL 处理

```
a. PATCH 原消息: auto_flag = 'human'

b. POST office_messages（飞书通知触发）:
   - msg_type: 'sys'
   - to_member_id: 原消息的 member_id 对应的人类
   - content: "[需审批] {原消息摘要}。原因：{为什么需要人类审批}"
   - auto_flag: 'pending'
   - priority_level: 1

c. 等待人类处理（本session不再处理该消息）
```

### 会话结束时

```
7. 更新token使用量
   PATCH office_config WHERE key='token_budget_{MY_ID}'
   value.used_today += 本session消耗

8. 上报状态
   PATCH office_agents SET status='idle' WHERE id='{MY_ID}'

9. 发送签退消息（广播）
```

## 自主响应规则清单

### 可自动回复（不经过人）

| 编号 | 场景 | 数据来源 | 回复模板 |
|------|------|---------|---------|
| A1 | 查询已记录的设计决策 | office_decisions WHERE title ILIKE '%关键词%' | "根据决策记录[title]：[body]" |
| A2 | 查询任务状态/进度 | office_tasks WHERE id=X | "[title] 当前状态：[status]，进度：[progress]%" |
| A3 | 查询成员当前状态 | office_agents WHERE id=X | "[human_name] 当前 [status]，在做：[task]" |
| A4 | 查询已确认的接口定义 | office_config WHERE key LIKE 'api_spec_%' | "接口定义如下：[value]" |
| A5 | 查询已确认的数据表结构 | office_config WHERE key LIKE 'table_spec_%' | "表结构如下：[value]" |
| A6 | 确认性回复 | 收到 update/progress 类消息 | "收到，已记录。" |
| A7 | 回复自己的任务进度 | 自己的 office_tasks | "我负责的[title]目前[progress]%" |
| A8 | 查询文档位置 | office_config WHERE key LIKE 'doc_index_%' | "文档在：[路径/URL]" |

### 需要人类审批

| 编号 | 触发条件 | 通知方式 |
|------|---------|---------|
| H1 | 预估token > 2000 | sys消息 → 飞书 |
| H2 | 预估token > 10000 | sys消息 → 飞书 + @人 |
| H3 | 修改已确认的设计方案 | sys消息 + approval消息 |
| H4 | 新增/删除功能 | sys消息 → 飞书 |
| H5 | 请求内容有歧义 | sys消息，附Agent理解和需要澄清的点 |
| H6 | 外部操作（git push/发布/支付） | sys消息 → 飞书 + @人 |
| H7 | 新增外部依赖 | sys消息 → 飞书 |
| H8 | 跨成员权限操作 | sys消息 → 飞书 + @两方人类 |
| H9 | 当日token预算耗尽 | sys消息，拒绝执行 |

## Token预算管理

每个成员在 office_config 中有一条 `token_budget_{member_id}` 记录：

```json
{
  "daily_limit": 50000,
  "used_today": 0,
  "reset_at": "2026-04-04T00:00:00Z"
}
```

- 每次自动回复后更新 used_today
- used_today >= daily_limit * 0.8 → 写sys预警消息
- used_today >= daily_limit → 停止自动回复，全部转人类审批
- 每日零点重置（由Agent自行判断 reset_at 是否过期）

## 飞书通知机制

Agent不直接调用飞书API。需要飞书通知时：

1. 写一条 `msg_type=sys` 的消息到 office_messages
2. 飞书Bot侧轮询未处理的sys消息并转发给对应人类
3. 转发后Bot将消息标记为 `auto_flag=done`

飞书通知配置存储在 office_config key=`feishu_notify_config`。

## 接口定义预写入

已确认的接口定义和表结构存储在 office_config 中，供所有Agent自动查询：

| key格式 | 内容 |
|---------|------|
| api_spec_{模块名} | API接口定义JSON |
| table_spec_{表名} | 数据表结构JSON |
| doc_index_{文档名} | 文档路径/URL |

这些数据由制作人（宇昂）写入和维护，其他Agent只读。

## 消息示例

### 查询接口定义（自动回复场景）

爱芮发送：
```json
{
  "from_name": "爱芮",
  "member_id": "antian",
  "to_member_id": "qianyuang",
  "msg_type": "query",
  "content": "wallets表的结构是什么？",
  "auto_flag": "pending",
  "token_est": 300,
  "priority_level": 2
}
```

宇昂的Agent自动回复：
```json
{
  "from_name": "研究局局长",
  "member_id": "qianyuang",
  "to_member_id": "antian",
  "msg_type": "auto_reply",
  "reply_to": "<原消息UUID>",
  "content": "wallets表结构如下：[从office_config key=table_spec_wallets读取]",
  "auto_flag": "done",
  "token_est": 400,
  "priority_level": 2
}
```

### 方案变更请求（人类审批场景）

爱芮发送：
```json
{
  "from_name": "爱芮",
  "member_id": "antian",
  "to_member_id": "qianyuang",
  "msg_type": "request",
  "content": "建议把CC充值比例从1:10改为1:5，理由是...",
  "auto_flag": "pending",
  "token_est": 0,
  "priority_level": 2
}
```

宇昂的Agent处理：
1. 判断为"修改已确认方案" → H3
2. PATCH 原消息 auto_flag='human'
3. POST sys消息通知宇昂审批

## 待A梦执行的SQL

```sql
-- V2协议：扩展office_messages表
ALTER TABLE office_messages
  ADD COLUMN IF NOT EXISTS to_member_id text,
  ADD COLUMN IF NOT EXISTS reply_to uuid REFERENCES office_messages(id),
  ADD COLUMN IF NOT EXISTS auto_flag text DEFAULT 'pending'
    CHECK (auto_flag IN ('auto','human','pending','done')),
  ADD COLUMN IF NOT EXISTS token_est int DEFAULT 0,
  ADD COLUMN IF NOT EXISTS priority_level int DEFAULT 2
    CHECK (priority_level IN (1,2,3));

-- 为定向消息查询添加索引
CREATE INDEX IF NOT EXISTS idx_messages_to_member
  ON office_messages(to_member_id, auto_flag, created_at);
```

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V1.0 | 2026-03 | 初始版本，纯异步留言板 |
| V2.0 | 2026-04-03 | 增加定向路由、自主响应规则、token预算、飞书通知 |
