"""
LLM客户端
"""

import os
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from app.utils.logger import setup_logger

# 加载环境变量
load_dotenv()

logger = setup_logger(__name__)


class LLMClient:
    """LLM客户端，支持多种模型"""
    
    def __init__(self, model_name: str = None):
        """初始化LLM客户端
        
        Args:
            model_name: 模型名称
        """
        if model_name is None:
            model_name = os.getenv("LLM_MODEL", "gpt-4o")
        
        self.model_name = model_name
        self.client = None
        
        try:
            self._initialize_client()
            logger.info(f"LLM客户端初始化成功: {model_name}")
        except Exception as e:
            logger.warning(f"LLM客户端初始化失败，使用模拟客户端: {str(e)}")
            self.client = None
    
    def _initialize_client(self):
        """初始化客户端"""
        try:
            if "gpt" in self.model_name.lower() or "openai" in self.model_name.lower():
                # OpenAI客户端
                from openai import AsyncOpenAI
                
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY未设置")
                
                self.client = AsyncOpenAI(api_key=api_key)
                self.client_type = "openai"
                
            else:
                # 其他模型（如本地模型）
                logger.warning(f"不支持的模型类型: {self.model_name}，使用模拟客户端")
                self.client = None
                self.client_type = "mock"
                
        except ImportError as e:
            logger.warning(f"导入LLM库失败: {str(e)}")
            self.client = None
            self.client_type = "mock"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成回答
        
        Args:
            prompt: 输入提示词
            **kwargs: 其他生成参数
            
        Returns:
            生成的回答
        """
        try:
            if self.client and self.client_type == "openai":
                return await self._generate_openai(prompt, **kwargs)
            else:
                return await self._generate_mock(prompt, **kwargs)
                
        except Exception as e:
            logger.error(f"生成回答时出错: {str(e)}")
            return "抱歉，生成回答时出现错误。请稍后重试。"
    
    async def _generate_openai(self, prompt: str, **kwargs) -> str:
        """使用OpenAI生成回答"""
        try:
            # 设置默认参数
            params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "你是一个专业的医疗AI助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "top_p": kwargs.get("top_p", 0.9)
            }
            
            response = await self.client.chat.completions.create(**params)
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI生成时出错: {str(e)}")
            raise
    
    async def _generate_mock(self, prompt: str, **kwargs) -> str:
        """模拟生成回答"""
        # 模拟异步处理
        await asyncio.sleep(1)
        
        # 基于关键词生成简单回答
        prompt_lower = prompt.lower()
        
        if "高血压" in prompt_lower:
            return self._get_hypertension_response()
        elif "糖尿病" in prompt_lower:
            return self._get_diabetes_response()
        elif "心脏病" in prompt_lower or "心血管" in prompt_lower:
            return self._get_heart_disease_response()
        elif "癌症" in prompt_lower or "肿瘤" in prompt_lower:
            return self._get_cancer_response()
        elif "感冒" in prompt_lower or "发烧" in prompt_lower:
            return self._get_cold_response()
        else:
            return self._get_general_response()
    
    def _get_hypertension_response(self) -> str:
        """高血压相关回答"""
        return """高血压是一种常见的慢性疾病，需要长期管理。

**定义和诊断标准：**
- 收缩压≥140mmHg和/或舒张压≥90mmHg
- 需要多次测量确认

**常见症状：**
- 头痛、头晕
- 心悸、胸闷
- 视力模糊
- 颈部僵硬

**治疗和管理：**
1. **生活方式干预：**
   - 低盐饮食（每日盐摄入<6g）
   - 规律运动（每周150分钟中等强度运动）
   - 戒烟限酒
   - 控制体重

2. **药物治疗：**
   - ACE抑制剂
   - ARB类药物
   - 钙通道阻滞剂
   - 利尿剂

**预防措施：**
- 定期监测血压
- 保持健康生活方式
- 管理其他危险因素"""
    
    def _get_diabetes_response(self) -> str:
        """糖尿病相关回答"""
        return """糖尿病是一组以高血糖为特征的代谢性疾病。

**主要类型：**
1. **1型糖尿病：** 胰岛素绝对缺乏
2. **2型糖尿病：** 胰岛素相对缺乏或胰岛素抵抗

**典型症状（"三多一少"）：**
- 多饮：口渴多饮水
- 多尿：尿量增加
- 多食：食欲亢进
- 体重减少

**诊断标准：**
- 空腹血糖≥7.0mmol/L
- 餐后2小时血糖≥11.1mmol/L
- 糖化血红蛋白≥6.5%

**管理方法：**
1. **血糖监测**
2. **饮食控制：** 控制总热量，合理分配三大营养素
3. **规律运动：** 有氧运动和抗阻运动结合
4. **药物治疗：** 根据病情选择合适药物
5. **并发症预防：** 定期检查眼底、肾功能等"""
    
    def _get_heart_disease_response(self) -> str:
        """心脏病相关回答"""
        return """心血管疾病是全球主要的死亡原因之一。

**常见类型：**
- 冠心病
- 心肌梗死
- 心律失常
- 心力衰竭

**危险因素：**
- 高血压
- 高血脂
- 糖尿病
- 吸烟
- 肥胖
- 缺乏运动

**预防措施：**
1. **控制危险因素**
2. **健康饮食：** 低脂、低盐、高纤维
3. **规律运动**
4. **戒烟限酒**
5. **定期体检**

**急性症状识别：**
- 胸痛、胸闷
- 呼吸困难
- 恶心、呕吐
- 出汗、乏力

如出现急性症状，应立即就医。"""
    
    def _get_cancer_response(self) -> str:
        """癌症相关回答"""
        return """癌症是一大类疾病的总称，需要专业诊断和治疗。

**早期筛查的重要性：**
- 提高治愈率
- 降低治疗成本
- 改善生活质量

**常见筛查项目：**
- 乳腺癌：乳腺X线摄影
- 宫颈癌：宫颈细胞学检查
- 结直肠癌：粪便潜血试验
- 肺癌：低剂量CT（高危人群）

**预防措施：**
1. **健康生活方式**
2. **戒烟限酒**
3. **均衡饮食**
4. **规律运动**
5. **避免致癌物质接触**
6. **定期体检**

**治疗方法：**
- 手术治疗
- 化疗
- 放疗
- 靶向治疗
- 免疫治疗

具体治疗方案需要专业医生制定。"""
    
    def _get_cold_response(self) -> str:
        """感冒相关回答"""
        return """感冒是常见的上呼吸道感染。

**常见症状：**
- 鼻塞、流涕
- 咽痛
- 咳嗽
- 发热
- 头痛、乏力

**治疗原则：**
1. **对症治疗为主**
2. **充分休息**
3. **多饮水**
4. **保持室内空气流通**

**药物治疗：**
- 解热镇痛药（发热时）
- 止咳药（干咳时）
- 抗组胺药（鼻塞时）

**预防措施：**
- 勤洗手
- 避免接触感染者
- 增强体质
- 接种流感疫苗

**就医指征：**
- 高热不退
- 呼吸困难
- 症状持续加重
- 出现并发症"""
    
    def _get_general_response(self) -> str:
        """通用回答"""
        return """根据您提供的医疗问题，我建议：

**一般健康建议：**
1. **保持健康生活方式**
   - 均衡饮食
   - 规律运动
   - 充足睡眠
   - 戒烟限酒

2. **定期健康检查**
   - 年度体检
   - 专科检查
   - 疫苗接种

3. **疾病预防**
   - 了解家族病史
   - 控制危险因素
   - 早期筛查

**就医建议：**
- 出现症状及时就医
- 遵循医生建议
- 按时服药
- 定期复查

**健康管理：**
- 建立健康档案
- 监测重要指标
- 学习健康知识
- 保持积极心态

如有具体健康问题，请咨询专业医生获得个性化建议。"""
    
    async def stream_generate(self, prompt: str, **kwargs):
        """流式生成回答"""
        try:
            if self.client and self.client_type == "openai":
                async for chunk in self._stream_generate_openai(prompt, **kwargs):
                    yield chunk
            else:
                # 模拟流式输出
                response = await self._generate_mock(prompt, **kwargs)
                words = response.split()
                
                for i in range(0, len(words), 3):  # 每次输出3个词
                    chunk = " ".join(words[i:i+3])
                    yield chunk + " "
                    await asyncio.sleep(0.1)  # 模拟延迟
                    
        except Exception as e:
            logger.error(f"流式生成时出错: {str(e)}")
            yield "生成回答时出现错误。"
    
    async def _stream_generate_openai(self, prompt: str, **kwargs):
        """OpenAI流式生成"""
        try:
            params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "你是一个专业的医疗AI助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "stream": True
            }
            
            async for chunk in await self.client.chat.completions.create(**params):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI流式生成时出错: {str(e)}")
            raise