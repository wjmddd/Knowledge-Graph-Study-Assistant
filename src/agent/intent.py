"""
意图分类模块
根据用户问题识别意图并提取实体
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class IntentType(str, Enum):
    """问题意图类型"""
    CONCEPT_DEFINITION = "concept_definition"  # 什么是X
    CONCEPT_COMPOSITION = "concept_composition"  # X由什么组成
    LEARNING_PATH = "learning_path"  # 学X需要什么基础
    COMPARE = "compare"  # X和Y有什么区别
    RELATION = "relation"  # X和Y有什么关系
    GENERAL = "general"  # 通用问题


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    entities: List[str]
    confidence: float
    raw_query: str


class IntentClassifier:
    """基于规则的意图分类器"""
    
    def __init__(self):
        # 定义意图模式
        self.patterns = {
            IntentType.CONCEPT_DEFINITION: [
                r"什么是(.+?)[？?]?$",
                r"(.+?)是什么[？?]?$",
                r"解释一下(.+)",
                r"(.+?)的定义",
                r"(.+?)的含义",
                r"介绍一下(.+)",
                r"请问(.+?)是什么",
            ],
            IntentType.CONCEPT_COMPOSITION: [
                r"(.+?)由.+组成",
                r"(.+?)包[含括]什么",
                r"(.+?)有哪些.+[部分组件]",
                r"(.+?)的组成",
                r"(.+?)的结构",
                r"(.+?)里面有什么",
                r"(.+?)包括哪些",
            ],
            IntentType.LEARNING_PATH: [
                r"学习?(.+?)需要.+[基础前提]",
                r"(.+?)的前置知识",
                r"学(.+?)之前.+学",
                r"(.+?)依赖什么",
                r"学习(.+?)的顺序",
                r"(.+?)的学习路径",
                r"先学什么.+再学(.+)",
            ],
            IntentType.COMPARE: [
                r"(.+?)和(.+?)[的有]什么区别",
                r"(.+?)与(.+?)[的有]什么不同",
                r"对比(.+?)和(.+)",
                r"比较(.+?)和(.+)",
                r"(.+?)和(.+?)的区别",
                r"(.+?)和(.+?)的异同",
                r"(.+?)跟(.+?)有什么差异",
            ],
            IntentType.RELATION: [
                r"(.+?)和(.+?)[有是]什么关系",
                r"(.+?)与(.+?)的关系",
                r"(.+?)怎么和(.+?)联系",
                r"(.+?)和(.+?)有什么联系",
                r"(.+?)和(.+?)相关吗",
            ],
        }
        
        # 编译正则表达式
        self.compiled_patterns = {}
        for intent, patterns in self.patterns.items():
            self.compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def classify(self, query: str) -> IntentResult:
        """
        分类用户问题的意图
        
        Args:
            query: 用户问题
            
        Returns:
            IntentResult 包含意图类型、提取的实体等
        """
        query = query.strip()
        
        # 依次尝试匹配各种意图
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(query)
                if match:
                    # 提取实体
                    entities = list(match.groups())
                    entities = [e.strip() for e in entities if e and e.strip()]
                    
                    return IntentResult(
                        intent=intent,
                        entities=entities,
                        confidence=0.9,
                        raw_query=query
                    )
        
        # 如果没有匹配，尝试提取关键实体
        entities = self._extract_entities(query)
        
        return IntentResult(
            intent=IntentType.GENERAL,
            entities=entities,
            confidence=0.5,
            raw_query=query
        )
    
    def _extract_entities(self, query: str) -> List[str]:
        """
        从问题中提取潜在实体
        简单的基于规则的实体提取
        """
        entities = []
        
        # 移除常见问句词
        clean_query = query
        stop_words = [
            "什么", "是", "有", "吗", "呢", "啊", "的", "吧", "么",
            "如何", "怎么", "怎样", "为什么", "哪些", "哪个", "哪里",
            "请问", "请", "告诉我", "说说", "讲讲", "介绍",
            "？", "?", "。", ".", "！", "!"
        ]
        for word in stop_words:
            clean_query = clean_query.replace(word, " ")
        
        # 分词（简单按空格和标点分割）
        tokens = re.split(r'[\s,，、;；]+', clean_query)
        tokens = [t.strip() for t in tokens if t.strip()]
        
        # 保留长度>=2的词作为潜在实体
        entities = [t for t in tokens if len(t) >= 2]
        
        # 识别常见的计算机术语模式
        cs_patterns = [
            r'[A-Z]{2,}',  # 大写缩写如 CPU, ALU
            r'[a-zA-Z]+\d+',  # 带数字的术语
            r'[\u4e00-\u9fa5]{2,}器',  # XX器 如 寄存器、处理器
            r'[\u4e00-\u9fa5]{2,}机',  # XX机 如 计算机、虚拟机
            r'[\u4e00-\u9fa5]{2,}码',  # XX码 如 补码、机器码
        ]
        
        for pattern in cs_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)
        
        # 去重并保持顺序
        seen = set()
        unique_entities = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique_entities.append(e)
        
        return unique_entities[:5]  # 最多返回5个实体


# 意图到工具的映射
INTENT_TO_TOOL = {
    IntentType.CONCEPT_DEFINITION: "get_concept_definition",
    IntentType.CONCEPT_COMPOSITION: "get_concept_composition",
    IntentType.LEARNING_PATH: "get_learning_path",
    IntentType.COMPARE: "compare_concepts",
    IntentType.RELATION: "find_path_between",
    IntentType.GENERAL: "hybrid_search",
}


def get_tool_for_intent(intent: IntentType) -> str:
    """根据意图获取对应的工具名称"""
    return INTENT_TO_TOOL.get(intent, "hybrid_search")


# 全局单例
_classifier: Optional[IntentClassifier] = None


def get_classifier() -> IntentClassifier:
    """获取全局分类器实例"""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_intent(query: str) -> IntentResult:
    """便捷函数：分类意图"""
    return get_classifier().classify(query)


if __name__ == "__main__":
    # 测试
    print("测试 IntentClassifier 模块...")
    classifier = IntentClassifier()
    
    test_queries = [
        "什么是补码？",
        "CPU由什么组成？",
        "学习虚拟内存需要什么基础？",
        "SRAM和DRAM有什么区别？",
        "CPU和ALU有什么关系？",
        "流水线冒险怎么解决？",
        "cache是怎么工作的",
    ]
    
    print("\n意图分类测试结果:")
    print("-" * 60)
    
    for query in test_queries:
        result = classifier.classify(query)
        print(f"\n问题: {query}")
        print(f"  意图: {result.intent.value}")
        print(f"  实体: {result.entities}")
        print(f"  置信度: {result.confidence}")
        print(f"  推荐工具: {get_tool_for_intent(result.intent)}")

