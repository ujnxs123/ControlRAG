import xml.etree.ElementTree as ET

# 解析GraphML文件
tree = ET.parse('./server/rag_storage/graph_chunk_entity_relation.graphml')
root = tree.getroot()

# 定义命名空间（GraphML 使用默认命名空间）
ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

# 存储提取的关系
relations = []

# 遍历所有 <edge> 元素
for edge in root.findall(".//g:edge", ns):
    source = edge.get("source").strip('"')  # 去除多余的引号
    target = edge.get("target").strip('"')
    
    # 提取 d5（关系类型）
    d5 = edge.find('.//g:data[@key="d5"]', ns)
    if d5 is not None:
        relation_type = d5.text.strip('"')  # 去除引号
        relations.append(f"({source}, {relation_type}, {target})")

# 写入 TXT 文件
with open("./server/rag_storage/relations.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(relations))

print(f"已提取 {len(relations)} 条关系，并保存到 relations.txt")