import streamlit as st
import requests
import json
import base64
import datetime
import re
from streamlit_agraph import agraph, Node, Edge, Config

# 配置Ollama服务器地址
OLLAMA_URL = "http://localhost:9621/api/chat"
MODEL_MANAGEMENT_URL = "http://localhost:9621/api"

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_model" not in st.session_state:
    st.session_state.current_model = "llama3"
if "models" not in st.session_state:
    st.session_state.models = []
# 设置系统提示词工程
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are a helpful assistant."

CUSTOM_CSS = """
<style>
    /* 基础样式重置 */
    .block-container {
        max-width: 900px;
        margin: auto;
        padding-top: 1rem;
        padding-bottom: 4rem; /* 为固定输入框预留空间 */
    }

    /* 消息容器弹性布局 */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
        padding: 1rem;
    }

    /* 消息气泡通用样式 */
    .stChatMessage {
        border-radius: 1.2rem;
        padding: 0.8rem 1.2rem;
        max-width: 75%;
        font-size: 1rem;
        line-height: 1.4;
        position: relative;
        word-wrap: break-word;
        background-color: #ECECEC;
        margin: 0;
    }

    /* 用户消息样式 */
    .stChatMessage[data-role="user"] {
        align-self: flex-end;
        background-color: #DCF8C6;
        border-bottom-right-radius: 0.3rem;
    }

    /* 用户消息气泡箭头 */
    .stChatMessage[data-role="user"]::after {
        content: '';
        position: absolute;
        bottom: 0;
        right: -0.5rem;
        width: 0;
        height: 0;
        border: 0.5rem solid transparent;
        border-left-color: #DCF8C6;
        border-bottom: none;
    }

    /* 助手消息样式 */
    .stChatMessage[data-role="assistant"] {
        align-self: flex-start;
        background-color: #ECECEC;
        border-bottom-left-radius: 0.3rem;
    }

    /* 助手消息气泡箭头 */
    .stChatMessage[data-role="assistant"]::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: -0.5rem;
        width: 0;
        height: 0;
        border: 0.5rem solid transparent;
        border-right-color: #ECECEC;
        border-bottom: none;
    }

    /* 消息时间戳 */
    .message-timestamp {
        font-size: 0.7rem;
        color: #666;
        margin-top: 0.3rem;
        text-align: right;
    }

    /* 头像图标 */
    .message-avatar {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        position: absolute;
        top: 0.5rem;
        font-size: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* 用户头像位置 */
    .stChatMessage[data-role="user"]::before {
        content: '👤';
        @extend .message-avatar;
        right: -32px;
    }

    /* 助手头像位置 */
    .stChatMessage[data-role="assistant"]::before {
        content: '🤖';
        @extend .message-avatar;
        left: -32px;
    }
    .image-container {
    display: flex;
    justify-content: center;
    margin: 0.5rem 0;
}
    .stImage {
    border-radius: 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}


</style>
"""
# sd 设置
def get_sd_models():
    """获取可用模型列表"""
    try:
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/sd-models")
        return [model['title'] for model in response.json()]
    except:
        st.error("无法连接Stable Diffusion服务器，请确认服务是否启动")
        return []

def get_sd_options():
    """获取当前配置选项"""
    try:
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/options")
        return response.json()
    except:
        return {}
def get_samplers():
    """动态获取可用采样器列表"""
    try:
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/samplers")
        if response.status_code == 200:
            return [sampler['name'] for sampler in response.json()]
        else:
            st.warning("使用默认采样器列表（API 返回非 200 状态码）")
            return ["Euler a", "DPM++ 2M Karras", "LMS", "DDIM", "UniPC"]
    except Exception as e:
        st.warning(f"使用默认采样器列表（连接失败: {str(e)})")
        return ["Euler a", "DPM++ 2M Karras", "LMS", "DDIM", "UniPC"]

def generate_image(response, sampler="Euler a", steps=20,
                  cfg_scale=7.0, width=512, height=512):
    """调用SD生成图片（实时参数传递）"""
    payload = {
        "prompt": response,
        "negative_prompt": "bad quality",
        "sampler_index": sampler,  # 使用传入的采样器
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        # 固定参数（可选）
        "restore_faces": True,  # 自动修复人脸
        "tiling": False
    }

    try:
        response = requests.post(
            "http://127.0.0.1:7860/sdapi/v1/txt2img",
            json=payload
        )
        return base64.b64decode(response.json()['images'][0])
    except Exception as e:
        st.error(f"图片生成失败: {str(e)}")
        return None

# 获取模型列表 ollma 设置------------------------------------------------------------
def get_models():
    try:
        response = requests.get(f"{MODEL_MANAGEMENT_URL}/tags")
        if response.status_code == 200:
            return [model["name"] for model in response.json()["models"]]
    except Exception as e:
        st.error(f"获取模型列表失败: {str(e)}")
    return ["llama3"]

# 拉取新模型
# def pull_model(model_name):
#     try:
#         response = requests.post(
#             f"{MODEL_MANAGEMENT_URL}/pull",
#             json={"name": model_name},
#             stream=True
#         )
#         return response.status_code == 200
#     except Exception as e:
#         st.error(f"拉取模型失败: {str(e)}")
#         return False

# 设置页面
def management():
    st.sidebar.header("🤖 模型管理")

    # 获取当前模型列表
    available_models = get_models()

    st.session_state.models = available_models

    # 模型选择器
    selected_model = st.sidebar.selectbox(
        "选择当前模型",
        options=available_models,
        index=available_models.index(st.session_state.current_model)
            if st.session_state.current_model in available_models else 0,
        key="model_select"
    )

    st.session_state.current_model = selected_model

    st.sidebar.markdown("---")

    # 拉取新模型输入框
    # new_model = st.sidebar.text_input("拉取新模型")
    # if st.sidebar.button("📥 拉取模型", key="pull_model_button") and new_model:
    #     with st.spinner("正在拉取模型，请稍候..."):
    #         if pull_model(new_model):
    #             st.success(f"模型 {new_model} 拉取成功！")
    #             st.session_state.models = get_models()
    #             st.rerun()
    #         else:
    #             st.error(f"模型 {new_model} 拉取失败，请检查名称或网络连接。")
# 回答模式选择列表
    answer_modes = {
        "混合": "/mix",
        "局部": "/local",
        "混合成": "/hybrid",
        "原生": "/naive",
        "全局": "/global",
        "仅聊天": "/bypass"
    }

    selected_mode = st.sidebar.selectbox(
        "🧠 回答模式",
        options=list(answer_modes.keys()),
        index=0,
        key="answer_mode_select"
    )
    st.session_state.answer_mode = answer_modes[selected_mode]

    # sd管理界面-----------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("🎨 文生图参数")

    # 获取可用模型列表
    models = get_sd_models()
    selected_sd_model = st.sidebar.selectbox(
        "选择基础模型",
        models,
        index=0 if not models else models.index(st.session_state.get('last_sd_model', '')) if 'last_sd_model' in st.session_state else 0,
        key="sd_model_select"
    )
    # 获取sample，sample自选
    available_samplers = get_samplers()

    # 获取当前配置
    current_sampler = "Euler a"
    if 'sd_params' in st.session_state:
        current_sampler = st.session_state.sd_params.get('sampler', 'Euler a')

    # 采样器选择器
    selected_sampler = st.sidebar.selectbox(
        "选择采样器",
        options=available_samplers,
        index=available_samplers.index(current_sampler) if current_sampler in available_samplers else 0,
        key="sampler_select"
    )


    # 保存当前模型到session_state（供绘图使用）
    st.session_state.current_sd_model = selected_sd_model

    # 动态参数设置（不保存）
    st.session_state.sd_params = {
        "sampler": selected_sampler,
        "steps": st.sidebar.slider("采样步数", 1, 150, 20),
        "cfg_scale": st.sidebar.slider("提示词相关性", 1.0, 30.0, 7.0, 0.5),
        "width": st.sidebar.number_input("图像宽度", 64, 4096, 512, 64),
        "height": st.sidebar.number_input("图像高度", 64, 4096, 512, 64)
    }
    # 保存配置


# 处理context上下文
def parse_knowledge_file(content):
    # 使用正则表达式提取各部分的 JSON 内容
    entities_match = re.search(r'-----Entities-----\s*```json\s*(.*?)\s*```', content, re.DOTALL)
    # relationships_match = re.search(r'-----Relationships-----\s*```json\s*(.*?)\s*```', content, re.DOTALL)


    # 解析为 Python 对象
    # entities = json.loads(entities_match.group(1)) if entities_match else []
    # relationships = json.loads(relationships_match.group(1)) if relationships_match else []
    if entities_match:
            try:
                # 解析JSON并提取entity字段
                entities = json.loads(entities_match.group(1))
                # 返回仅包含实体名称的列表
                return [item["entity"] for item in entities if "entity" in item]
            except json.JSONDecodeError:
                return []
    return []

def get_relationship(content):
    """
    从模型返回的文本中提取三元组 (head, relation, tail)
    返回格式为：[(head, relation, tail), ...]
    """
    relations = []
    relationships_match = re.search(r'-----Relationships-----\s*```json\s*(.*?)\s*```', content, re.DOTALL)

    if not relationships_match:
        print("未找到 Relationships 部分")
        return relations

    try:
        relationships = json.loads(relationships_match.group(1))
    except json.JSONDecodeError as e:
        print("JSON 解析失败:", str(e))
        return relations

    for idx, item in enumerate(relationships):
        try:
            source = item.get("source")
            target = item.get("target")
            keywords = item.get("keywords", "")

            if not all([source, target, keywords]):
                print(f"跳过第 {idx} 条：字段缺失 (source: {source}, target: {target}, keywords: {keywords})")
                continue

            # 提取关系类型
            main_keyword = keywords.split('<SEP>')[0].strip()
            relation_type = main_keyword.split(',')[0].strip()

            # 构建元组并添加到结果中
            relations.append((source, relation_type, target))

        except Exception as e:
            print(f"处理第 {idx} 条时发生错误: {str(e)}")
            continue

    return relations

def generate_graph(relations):
    nodes = set()
    edges = []
    for subject, predicate, object in relations:
        nodes.add(subject)
        nodes.add(object)
        edges.append(Edge(source=subject, target=object, label=predicate))

    # Convert nodes to streamlit-agraph Node objects
    node_list = [Node(id=node, label=node, color="#87CEFA", size=15) for node in nodes]
    config = Config(
    width=1200,
    height=800,
    directed=True,
    nodeHighlightBehavior=True,
    highlightColor="#F7A7A6",
    collapsible=False,
    node={'labelProperty': 'label'},
    link={'labelProperty': 'label', 'renderLabel': True},
    hierarchical=True,  # Use hierarchical layout for large graphs
    zoom=1.0
    )
    return agraph(nodes=node_list, edges=edges, config=config)

# 调用Ollama API
def get_ollama_stream_response(messages, model, system_prompt):
    headers = {"Content-Type": "application/json"}
    # 添加前缀
    if messages and st.session_state.get("answer_mode", "/mix") != "/mix":
        modified_messages = [dict(msg) for msg in messages]  # 创建副本避免修改原始数据
        modified_messages[-1] = dict(modified_messages[-1])  # 复制最后一条消息
        modified_messages[-1]["content"] = f"{st.session_state.answer_mode} {modified_messages[-1]['content']}"
    else:
        modified_messages = messages

    data = {
        "model": model,
        "messages": modified_messages,  # 使用修改后的消息列表
        "stream": True,
        "system": system_prompt
    }


    try:
        response = requests.post(
            OLLAMA_URL,
            headers=headers,
            json=data,
            stream=True
        )

        if response.status_code == 200:
            full_response = ""
            message_placeholder = st.empty()

            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line)
                        if "message" in json_response and "content" in json_response["message"]:
                            content = json_response["message"]["content"]
                            full_response += content
                            message_placeholder.markdown(full_response + "▌")
                        if json_response.get("done", False):
                            message_placeholder.markdown(full_response)
                            return full_response
                    except json.JSONDecodeError:
                        continue
            return full_response
        else:
            return f"错误: {response.status_code} - {response.text}"
    except Exception as e:
        return f"请求失败: {str(e)}"


def get_context(messages, model, system_prompt):
    headers = {"Content-Type": "application/json"}
    # 添加前缀

    modified_messages = [dict(msg) for msg in messages]  # 创建副本避免修改原始数据
    modified_messages[-1] = dict(modified_messages[-1])  # 复制最后一条消息
    modified_messages[-1]["content"] = "/context " + modified_messages[-1]["content"]

    data = {
        "model": model,
        "messages": modified_messages,  # 使用修改后的消息列表
        "stream": True,
        "system": system_prompt
    }


    try:
        response = requests.post(
            OLLAMA_URL,
            headers=headers,
            json=data,
            stream=True
        )

        if response.status_code == 200:
            full_response = ""
            message_placeholder = st.empty()

            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line)
                        if "message" in json_response and "content" in json_response["message"]:
                            content = json_response["message"]["content"]
                            full_response += content
                            message_placeholder.markdown(full_response + "▌")
                        if json_response.get("done", False):
                            message_placeholder.markdown(full_response)
                            return full_response
                    except json.JSONDecodeError:
                        continue
            return full_response
        else:
            return f"错误: {response.status_code} - {response.text}"
    except Exception as e:
        return f"请求失败: {str(e)}"
# 模型管理界面


# 聊天界面
def chat_interface():

    # 注入自定义CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    enable_image_gen = st.sidebar.checkbox("🎨 启用文生图功能", value=False)
    enable_mermaid = st.sidebar.checkbox(
        "📊 启用知识图谱",
        value=False,
    )
    st.title("💬 ControlRAG 自控教学助手")

    # 创建固定高度的聊天容器
    chat_container = st.container()

    # 显示消息历史（带时间戳）
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(f"""
                <div class="message-content">
                    {message["content"]}
                    <div class="message-timestamp">{message.get("timestamp", "")}</div>
                </div>
                """, unsafe_allow_html=True)

    # 聊天输入框
    if prompt := st.chat_input("在此处输入消息..."):


        # 获取当前时间戳
        timestamp = datetime.datetime.now().strftime("%H:%M")

        # 添加用户消息到历史
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": timestamp
        })

        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(f"""
            <div class="message-content">
                {prompt}
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """, unsafe_allow_html=True)

        # 获取AI响应
        with st.chat_message("assistant"):
            response = get_ollama_stream_response(
                st.session_state.messages,
                st.session_state.current_model,
                st.session_state.system_prompt
            )

            # 添加时间戳
            timestamp = datetime.datetime.now().strftime("%H:%M")

            # 将AI响应添加到历史
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "timestamp": timestamp
            })

            st.markdown(f"""
            <div class="message-content">
                {response}
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """, unsafe_allow_html=True)
        # 生成相关知识点-----------------------------------------------------------
        if enable_mermaid:
            with st.chat_message("assistant"):
                context = get_context(
                    st.session_state.messages,
                    st.session_state.current_model,
                    st.session_state.system_prompt
                )
                entities = parse_knowledge_file(context)
                triplets = get_relationship(context)

            st.markdown(f"**检测到与以下知识点有关:** {', '.join(entities)}")
            st.markdown("### 📚 交互式知识图谱")
            with st.container():
                generate_graph(triplets)
        # 生图---------------------------------------------------------------


        if enable_image_gen:
            with st.chat_message("assistant"):
                with st.spinner("🎨 正在生成图片..."):
                    # 使用AI回答作为提示词生成图片
                    image_data = generate_image(response)

                    if image_data:
                        # 显示图片
                        st.image(image_data, use_container_width=True)

                        # 将图片信息存入历史记录
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "![Generated Image](data:image/png;base64," +
                                    base64.b64encode(image_data).decode() + ")"
                        })

# 主函数
def main():
    st.set_page_config(
    page_title="ControlRAG 自控知识教学助手",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)
    management()
    chat_interface()

if __name__ == "__main__":
    main()
