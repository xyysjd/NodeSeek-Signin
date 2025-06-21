from curl_cffi import requests
import time
import os
from typing import Dict, Optional, Any, Union

class TwoCaptchaSolverError(Exception):
    """2Captcha 解决器错误基类"""
    pass

class TwoCaptchaSolver:
    """
    2Captcha 验证码解决工具
    
    使用 2Captcha API 解决 Turnstile 验证码，获取验证令牌
    参考文档: https://2captcha.com/2captcha-api
    """
    
    def __init__(
        self, 
        api_key: str,
        api_base_url: str = "https://2captcha.com",
        max_retries: int = 20,
        retry_interval: int = 5,
        timeout: int = 60
    ):
        """
        初始化 2Captcha 验证码解决器
        
        参数:
            api_key: 2Captcha API 密钥
            api_base_url: API 基础 URL，默认为 2Captcha 官方节点
            max_retries: 最大重试次数
            retry_interval: 重试间隔(秒)
            timeout: 请求超时时间(秒)
        """
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.in_url = f"{api_base_url}/in.php"
        self.res_url = f"{api_base_url}/res.php"
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.timeout = timeout
    
    def solve(
        self,
        url: str,
        sitekey: str,
        user_agent: Optional[str] = None,
        verbose: bool = False
    ) -> str:
        """
        解决 Turnstile 验证并返回令牌
        
        参数:
            url: 目标网站 URL
            sitekey: Turnstile sitekey
            user_agent: 自定义 User-Agent
            verbose: 是否打印详细日志
            
        返回:
            验证令牌字符串
            
        异常:
            TwoCaptchaSolverError: 解决验证码时出错
        """
        if verbose:
            print("正在创建 2Captcha 验证任务...")
            
        task_id = self._create_task(url, sitekey, user_agent, verbose)
        if not task_id:
            raise TwoCaptchaSolverError("创建验证码任务失败")
            
        # 获取任务结果
        token = self._get_task_result(task_id, verbose)
        if not token:
            raise TwoCaptchaSolverError("获取验证码结果失败")
            
        if verbose:
            print(f"验证码解决成功: {token[:30]}...{token[-10:] if len(token) > 30 else ''}")
            
        return token
        
    def _create_task(
        self,
        url: str,
        sitekey: str,
        user_agent: Optional[str] = None,
        verbose: bool = False
    ) -> Optional[str]:
        """创建验证码任务并返回任务ID"""
        
        # 准备任务数据 - 2Captcha格式
        params = {
            "key": self.api_key,
            "method": "turnstile",
            "sitekey": sitekey,
            "pageurl": url,
            "json": 1  # 返回JSON格式结果
        }
        
        # 如果需要添加用户代理
        if user_agent:
            params["userAgent"] = user_agent
            
        try:
            if verbose:
                print(f"发送创建任务请求...")
                
            response = requests.get(
                self.in_url, 
                params=params,
                timeout=self.timeout,
                impersonate="chrome110"
            )
            result = response.json()
            
            if verbose:
                print(f"创建任务响应: {result}")
                
            if result.get("status") == 1:
                task_id = result.get("request")
                if verbose:
                    print(f"成功创建任务，ID: {task_id}")
                return task_id
            else:
                error_desc = result.get('error_text', '未知错误')
                if verbose:
                    print(f"创建任务失败: {error_desc}")
                return None
                
        except Exception as e:
            if verbose:
                print(f"创建任务过程中发生异常: {e}")
            return None
    
    def _get_task_result(self, task_id: str, verbose: bool = False) -> Optional[str]:
        """获取任务结果"""
        
        params = {
            "key": self.api_key,
            "action": "get",
            "id": task_id,
            "json": 1  # 返回JSON格式结果
        }
        
        for attempt in range(1, self.max_retries + 1):
            try:
                if verbose:
                    print(f"尝试获取任务结果 ({attempt}/{self.max_retries})...")
                    
                response = requests.get(
                    self.res_url,
                    params=params,
                    timeout=self.timeout,
                    impersonate="chrome110"
                )
                result = response.json()
                
                if result.get("status") == 0:
                    error_desc = result.get('request', '未知错误')
                    # 如果是CAPCHA_NOT_READY错误，表示正在处理中
                    if error_desc == "CAPCHA_NOT_READY":
                        if verbose:
                            print(f"任务处理中，等待 {self.retry_interval} 秒后重试...")
                        time.sleep(self.retry_interval)
                        continue
                    else:
                        if verbose:
                            print(f"获取结果失败: {error_desc}")
                        return None
                
                # 状态为1表示已完成
                if result.get("status") == 1:
                    token = result.get("request")
                    if verbose:
                        print("任务已完成")
                    return token
                    
            except Exception as e:
                if verbose:
                    print(f"获取任务结果过程中发生异常: {e}")
                return None
                
        if verbose:
            print("获取任务结果超时")
        return None

"""
# 简单使用示例
if __name__ == "__main__":
    # 示例用法
    api_key = "YOUR_2CAPTCHA_API_KEY"
    
    solver = TwoCaptchaSolver(
        api_key=api_key,
        verbose=True
    )
    try:
        token = solver.solve(
            url="https://www.nodeseek.com/signIn.html",
            sitekey="0x4AAAAAAAaNy7leGjewpVyR"
        )
        print("成功获取令牌！")
        print(f"令牌: {token[:30]}...{token[-10:]}")
    except TwoCaptchaSolverError as e:
        print(f"解决 Turnstile 验证码失败: {e}")
""" 