# -*- coding: utf-8 -*-
"""写入V3方案表结构和文档索引到Supabase office_config"""
import urllib.request, json, ssl, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ctx = ssl.create_default_context()
SB = 'https://elnzkemqcmdqefwyldoh.supabase.co'
KEY = 'sb_publishable_dqOvhjfZLECtQNvcX5JIqg_p8iojSMN'

def post_config(key, value, owner='qianyuang'):
    v = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
    data = json.dumps({'key': key, 'value': v, 'owner': owner}).encode('utf-8')
    req = urllib.request.Request(f'{SB}/rest/v1/office_config', data=data, headers={
        'apikey': KEY, 'Authorization': f'Bearer {KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'
    })
    try:
        urllib.request.urlopen(req, context=ctx)
        print(f'OK: {key}')
    except Exception as e:
        body = e.read().decode() if hasattr(e, 'read') else str(e)
        print(f'ERR {key}: {body}')

# 10张新表结构
specs = {
    'wallets': [
        'id UUID PK', 'user_id UUID FK', 'cc_balance BIGINT (CC余额)',
        'cc_total_charged BIGINT', 'cc_total_earned BIGINT', 'cc_total_withdrawn BIGINT',
        'created_at TIMESTAMPTZ', 'updated_at TIMESTAMPTZ'
    ],
    'transactions': [
        'id UUID PK', 'from_user_id UUID FK (付款方,NULL=系统)',
        'to_user_id UUID FK (收款方,NULL=系统)', 'amount BIGINT',
        'tx_type TEXT (charge/purchase/bounty_pay/hire_pay/withdraw/subscription/platform_fee)',
        'reference_id UUID', 'status TEXT (pending/completed/failed/refunded)', 'created_at TIMESTAMPTZ'
    ],
    'subscriptions': [
        'id UUID PK', 'user_id UUID FK', 'plan TEXT (resident/pro_creator/agent_team)',
        'status TEXT (active/expired/cancelled)', 'started_at TIMESTAMPTZ',
        'expires_at TIMESTAMPTZ', 'auto_renew BOOLEAN', 'payment_method TEXT (cc/wechat/alipay)'
    ],
    'reputation_logs': [
        'id UUID PK', 'user_id UUID FK', 'rep_change INT (正=获得,负=扣除)',
        'reason TEXT (skill_published/installed/review/bounty/hire/decay/penalty)',
        'reference_id UUID', 'source_user_id UUID', 'is_suspicious BOOLEAN', 'created_at TIMESTAMPTZ'
    ],
    'hire_orders': [
        'id UUID PK', 'requester_id UUID FK (雇佣方)', 'provider_id UUID FK (被雇佣方)',
        'title TEXT', 'required_skills TEXT[]', 'budget_cc BIGINT',
        'status TEXT (open/matched/in_progress/delivered/completed/disputed/cancelled)',
        'deadline TIMESTAMPTZ', 'deliverable_url TEXT'
    ],
    'agent_services': [
        'id UUID PK', 'user_id UUID FK', 'title TEXT', 'skill_ids UUID[]',
        'price_cc BIGINT', 'price_type TEXT (per_task/per_hour)',
        'is_available BOOLEAN', 'avg_rating NUMERIC(3,2)', 'total_orders INT'
    ],
    'achievements': [
        'id UUID PK', 'user_id UUID FK', 'achievement_key TEXT',
        'unlocked_at TIMESTAMPTZ', 'reward_claimed BOOLEAN'
    ],
    'cosmetic_items': [
        'id UUID PK', 'name TEXT', 'category TEXT (hat/aura/emote)',
        'rarity TEXT (common/rare/epic/legendary)', 'price_cc INT',
        'asset_url TEXT', 'is_limited BOOLEAN'
    ],
    'user_cosmetics': [
        'id UUID PK', 'user_id UUID FK', 'item_id UUID FK->cosmetic_items',
        'acquired_at TIMESTAMPTZ', 'acquire_method TEXT (cc_purchase/achievement/event)'
    ],
    'escrow_orders': [
        'id UUID PK', 'trade_type TEXT (bounty/hire/skill_purchase)',
        'reference_id UUID', 'buyer_id UUID FK', 'seller_id UUID FK',
        'amount_cc BIGINT', 'platform_fee_cc BIGINT',
        'status TEXT (frozen/released/refunded/disputed)',
        'frozen_at TIMESTAMPTZ', 'released_at TIMESTAMPTZ'
    ],
}

for tname, fields in specs.items():
    post_config(f'table_spec_{tname}', {'table': tname, 'fields': fields})

# 文档索引
post_config('doc_index_v3', {
    'title': 'AgentTown落地方案V3',
    'path': 'C:/Users/qianyuang1/策划技能研究局/社区发展/AgentTown-LandingPlan-V3.docx',
    'version': '3.0', 'date': '2026-04-03'
})
post_config('doc_index_phase1', {
    'title': 'AgentTown Phase1游戏性设计V2',
    'path': 'C:/Users/qianyuang1/策划技能研究局/社区发展/AgentTown-Phase1-GameplayDesign.docx',
    'version': '2.0'
})
post_config('doc_index_protocol_v2', {
    'title': 'Agent协作协议V2',
    'path': 'C:/Users/qianyuang1/策划技能研究局/学习资料/AGENT-PROTOCOL-V2.md',
    'version': '2.0'
})

print('Done: all specs + indexes written')
