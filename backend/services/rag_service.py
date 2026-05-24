import logging
import os
import glob
from pathlib import Path

import numpy as np

from config import settings
from database import get_knowledge_items, add_knowledge_item

logger = logging.getLogger("app.rag")

# Knowledge directory (project root / 知识库)
_KNOWLEDGE_DIR = str(Path(__file__).resolve().parent.parent.parent / "知识库")

os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

model = None
index = None
knowledge_cache: list = []
model_initialized = False
rag_enabled = False


def init_model():
    global model, index, model_initialized, rag_enabled
    if model_initialized:
        return

    try:
        from sentence_transformers import SentenceTransformer
        import faiss

        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        index = faiss.IndexFlatL2(settings.EMBEDDING_DIM)
        model_initialized = True
        rag_enabled = True
        logger.info("向量模型初始化成功")
        load_knowledge_base()
    except Exception:
        logger.warning("初始化向量模型失败（网络原因），RAG功能不可用", exc_info=True)
        model = None
        index = None
        rag_enabled = False


def load_knowledge_base():
    global knowledge_cache
    try:
        knowledge_items = get_knowledge_items(limit=500)
        if not knowledge_items:
            init_default_knowledge()
            knowledge_items = get_knowledge_items(limit=500)

        knowledge_cache = knowledge_items

        if model and index:
            db_count = len(knowledge_items)
            imported_count = import_knowledge_files(_KNOWLEDGE_DIR)
            all_items = get_knowledge_items(limit=500)
            knowledge_cache = all_items

            index.reset()
            texts = [item["content"] for item in all_items]
            embeddings = model.encode(texts)
            index.add(np.array(embeddings))

            logger.info("知识库已加载 DB:%d + 文件导入:%d = 总计 %d 条记录",
                        db_count, imported_count, len(all_items))
        else:
            import_knowledge_files(_KNOWLEDGE_DIR)
            logger.info("知识库已加载 %d 条记录（无向量索引）", len(knowledge_cache))
    except Exception:
        logger.warning("加载知识库失败", exc_info=True)


def init_default_knowledge():
    default_knowledge = [
        {
            "title": "常见疾病科普-感冒",
            "content": "感冒是一种常见的上呼吸道感染性疾病，主要由病毒引起。常见症状包括流鼻涕、打喷嚏、喉咙痛、咳嗽、轻度发热等。通常一周左右可自行恢复，建议多喝水、休息充足。如症状持续或加重，应及时就医。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "常见病科普",
        },
        {
            "title": "常见疾病科普-高血压",
            "content": "高血压是指血压持续升高的慢性疾病。早期可能无明显症状，长期可引发心脑血管并发症。建议定期测量血压，保持低盐饮食、规律运动。确诊后应遵医嘱服药，定期复查。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "常见病科普",
        },
        {
            "title": "常见疾病科普-糖尿病",
            "content": "糖尿病是一种代谢性疾病，特征是血糖水平持续升高。主要分为1型和2型。患者需要控制饮食、规律运动、监测血糖，并可能需要药物治疗。定期随访和健康教育非常重要。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "常见病科普",
        },
        {
            "title": "挂号流程",
            "content": "患者可通过医院官方网站、手机App、电话或现场窗口进行挂号。建议提前预约，携带有效身份证件。部分医院支持在线支付挂号费。就诊前请提前30分钟到达医院。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "就医指南",
        },
        {
            "title": "医保政策",
            "content": "我国基本医疗保险覆盖范围包括门诊、住院、药品等。参保人员可享受一定比例的费用报销。异地就医需提前办理备案手续。具体报销比例和范围请咨询当地医保部门。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "医保政策",
        },
        {
            "title": "科室介绍-内科",
            "content": "内科主要诊治成人的各种非手术疾病，包括心血管、呼吸、消化、内分泌等系统疾病。常见就诊原因包括高血压、糖尿病、感冒、消化不良等。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "科室介绍",
        },
        {
            "title": "科室介绍-外科",
            "content": "外科主要处理需要手术治疗的疾病，包括创伤、肿瘤、畸形矫正等。常见手术包括阑尾炎切除术、骨折复位、肿瘤切除等。术前需进行全面检查评估。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "科室介绍",
        },
        {
            "title": "科室介绍-妇产科",
            "content": "妇产科负责女性生殖系统疾病的诊治和孕产妇保健。包括妇科炎症、肿瘤、月经不调、孕期检查、分娩等。建议女性定期进行妇科检查。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "科室介绍",
        },
        {
            "title": "科室介绍-儿科",
            "content": "儿科主要为0-14岁儿童提供医疗服务。包括儿童常见病、多发病的诊治，预防接种，生长发育评估等。儿童用药需严格遵循医嘱。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "科室介绍",
        },
        {
            "title": "健康生活方式",
            "content": "保持健康生活方式包括：均衡饮食、规律运动、充足睡眠、戒烟限酒、保持良好心态。建议成年人每周至少进行150分钟中等强度运动。定期体检有助于早期发现健康问题。",
            "source_url": "https://www.nhc.gov.cn",
            "category": "健康科普",
        },
    ]
    for item in default_knowledge:
        add_knowledge_item(item["title"], item["content"], item["source_url"], item["category"])


def import_knowledge_files(knowledge_dir: str = "知识库") -> int:
    """从 知识库/ 目录导入 .md 文件到 MySQL 知识库表和 FAISS 向量索引。

    每个 .md 文件按 ## 二级标题拆分为独立的知识条目，
    以文件名作为 category，标题作为 title。
    """
    if not os.path.isdir(knowledge_dir):
        logger.info("知识库目录 %s 不存在，跳过导入", knowledge_dir)
        return 0

    md_files = glob.glob(os.path.join(knowledge_dir, "**/*.md"), recursive=True)
    if not md_files:
        return 0

    imported = 0
    for filepath in md_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            filename = os.path.splitext(os.path.basename(filepath))[0]
            rel_path = os.path.relpath(filepath, knowledge_dir)
            category = os.path.dirname(rel_path) if os.path.dirname(rel_path) != "." else "通用"

            sections = _parse_markdown_sections(content)
            if not sections:
                full_content = content[:2000]
                title = filename
                add_knowledge_item(title, full_content, filepath, category)
                if model and index:
                    embedding = model.encode([full_content])
                    index.add(np.array(embedding))
                knowledge_cache.append({
                    "id": None, "title": title, "content": full_content,
                    "source_url": filepath, "category": category,
                })
                imported += 1
            else:
                for section_title, section_content in sections:
                    if len(section_content.strip()) < 20:
                        continue
                    add_knowledge_item(section_title, section_content[:2000], filepath, category)
                    if model and index:
                        embedding = model.encode([section_content[:2000]])
                        index.add(np.array(embedding))
                    knowledge_cache.append({
                        "id": None, "title": section_title, "content": section_content[:2000],
                        "source_url": filepath, "category": category,
                    })
                    imported += 1

            logger.info("知识库文件已导入: %s (%d 条)", filepath, imported if not sections else len(sections))
        except Exception:
            logger.warning("导入知识库文件失败: %s", filepath, exc_info=True)

    if imported > 0:
        logger.info("知识库文件导入完成，共 %d 条", imported)
    return imported


def _parse_markdown_sections(content: str) -> list:
    """将 Markdown 内容按 ## 标题拆分为 (标题, 内容) 列表。"""
    import re
    sections = []
    pattern = re.compile(r"^##\s+(.+)", re.MULTILINE)
    matches = list(pattern.finditer(content))

    if not matches:
        return []

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        sections.append((title, body))

    return sections


def search_knowledge_base(query: str, top_k: int = 5) -> list:
    if not rag_enabled:
        return []

    if not knowledge_cache:
        try:
            knowledge_items = get_knowledge_items(limit=500)
            knowledge_cache.extend(knowledge_items)
        except Exception:
            return []

    if not model or not index:
        return []

    try:
        query_embedding = model.encode([query])
        distances, indices = index.search(np.array(query_embedding), top_k)

        results = []
        for i in range(len(indices[0])):
            if indices[0][i] < len(knowledge_cache):
                item = knowledge_cache[indices[0][i]]
                item["score"] = float(distances[0][i])
                results.append(item)
        return results
    except Exception:
        logger.warning("搜索知识库失败", exc_info=True)
        return []


def add_knowledge_to_vector_db(title: str, content: str, source_url: str = None, category: str = None):
    if not rag_enabled:
        return add_knowledge_item(title, content, source_url, category)

    item_id = add_knowledge_item(title, content, source_url, category)
    if item_id and model and index:
        embedding = model.encode([content])
        index.add(np.array(embedding))
        knowledge_cache.append({
            "id": item_id, "title": title, "content": content,
            "source_url": source_url, "category": category,
        })
    return item_id


def get_knowledge_text(query: str) -> str:
    if not rag_enabled:
        return ""
    results = search_knowledge_base(query)
    if results:
        return "\n".join([f"{item['title']}: {item['content']}" for item in results[:3]])
    return ""


def is_rag_enabled() -> bool:
    return rag_enabled
