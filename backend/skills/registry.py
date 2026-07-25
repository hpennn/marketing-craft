"""
Skill Registry - 技能注册中心
负责注册、发现、加载技能
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class SkillMeta:
    """技能元数据"""
    id: str
    name: str
    icon: str
    description: str
    input_type: str  # "textarea", "file", "file+text"
    output_type: str  # "text", "file", "structured"
    handler: Optional[Callable] = None
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


class SkillRegistry:
    """技能注册中心 - 单例模式"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, skill: SkillMeta) -> None:
        """注册一个技能"""
        self._skills[skill.id] = skill

    def unregister(self, skill_id: str) -> None:
        """注销一个技能"""
        self._skills.pop(skill_id, None)

    def get(self, skill_id: str) -> Optional[SkillMeta]:
        """获取技能元数据"""
        return self._skills.get(skill_id)

    def list_all(self, enabled_only: bool = True) -> List[SkillMeta]:
        """列出所有技能"""
        skills = list(self._skills.values())
        if enabled_only:
            skills = [s for s in skills if s.enabled]
        return skills

    def find_by_keyword(self, keyword: str) -> List[SkillMeta]:
        """根据关键词匹配技能"""
        keyword_lower = keyword.lower()
        matched = []
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            if (keyword_lower in skill.name.lower() or
                keyword_lower in skill.description.lower() or
                any(keyword_lower in tag.lower() for tag in skill.tags)):
                matched.append(skill)
        return matched

    def find_by_keywords(self, text: str) -> Optional[SkillMeta]:
        """从文本中匹配最合适的技能"""
        keyword_map = {
            "xiaohongshu": ["小红书", "种草", "笔记", "安利", "推荐"],
            "video_script": ["视频", "短视频", "脚本", "抖音", "拍摄", "剪辑"],
            "seo_article": ["seo", "seo文章", "搜索引擎", "关键词优化", "排名"],
            "ad_copy": ["广告", "ad", "创意", "banner", "投放"],
            "product_desc": ["产品", "商品", "描述", "详情页", "电商"],
            "email_marketing": ["邮件", "edm", "营销邮件", "email", "群发"],
            "social_media": ["社媒", "社交", "微博", "公众号", "帖子", "朋友圈"],
            "marketing_plan": ["营销方案", "策划", "推广方案", "营销计划", "方案"],
        }
        text_lower = text.lower()
        for skill_id, keywords in keyword_map.items():
            if any(kw in text_lower for kw in keywords):
                skill = self.get(skill_id)
                if skill and skill.enabled:
                    return skill
        return None

    def load_preset_skills(self) -> None:
        """加载所有预置技能"""
        from skills.preset import xiaohongshu, video_script, seo_article, ad_copy
        from skills.preset import product_desc, email_marketing, social_media, marketing_plan

        preset_skills = [
            SkillMeta(
                id="xiaohongshu",
                name="小红书种草文",
                icon="❤️",
                description="生成小红书风格种草文",
                input_type="textarea",
                output_type="text",
                handler=xiaohongshu.execute,
                tags=["小红书", "种草", "笔记", "安利"],
            ),
            SkillMeta(
                id="video_script",
                name="短视频脚本",
                icon="🎬",
                description="生成短视频脚本",
                input_type="textarea",
                output_type="text",
                handler=video_script.execute,
                tags=["视频", "短视频", "脚本", "抖音"],
            ),
            SkillMeta(
                id="seo_article",
                name="SEO优化文章",
                icon="🔍",
                description="生成SEO优化文章",
                input_type="textarea",
                output_type="text",
                handler=seo_article.execute,
                tags=["SEO", "搜索引擎", "关键词", "排名"],
            ),
            SkillMeta(
                id="ad_copy",
                name="广告创意",
                icon="📢",
                description="生成多版本广告文案",
                input_type="textarea",
                output_type="text",
                handler=ad_copy.execute,
                tags=["广告", "创意", "banner", "投放"],
            ),
            SkillMeta(
                id="product_desc",
                name="产品描述",
                icon="🏷️",
                description="生成电商产品描述",
                input_type="textarea",
                output_type="text",
                handler=product_desc.execute,
                tags=["产品", "商品", "电商", "详情页"],
            ),
            SkillMeta(
                id="email_marketing",
                name="邮件营销",
                icon="📧",
                description="生成营销邮件",
                input_type="textarea",
                output_type="text",
                handler=email_marketing.execute,
                tags=["邮件", "EDM", "营销邮件"],
            ),
            SkillMeta(
                id="social_media",
                name="社媒内容",
                icon="🔗",
                description="生成社交媒体帖子",
                input_type="textarea",
                output_type="text",
                handler=social_media.execute,
                tags=["社媒", "社交", "微博", "公众号"],
            ),
            SkillMeta(
                id="marketing_plan",
                name="营销方案",
                icon="📊",
                description="生成完整营销方案",
                input_type="textarea",
                output_type="text",
                handler=marketing_plan.execute,
                tags=["营销方案", "策划", "推广方案"],
            ),
        ]

        for skill in preset_skills:
            self.register(skill)


# 全局实例
registry = SkillRegistry()
