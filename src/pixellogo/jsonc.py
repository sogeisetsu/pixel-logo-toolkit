"""极简 JSONC 解析：在标准 JSON 之上支持 ``//``、``/* */`` 注释与尾逗号。

不引入第三方依赖，也不放宽 JSON 的其他约束（字符串仍必须用双引号）。
"""
from __future__ import annotations

import json


class JsoncError(ValueError):
    """JSONC 语法错误。"""


def strip_comments(text: str) -> str:
    """去掉注释，保留字符串字面量的原样内容。"""
    out: list[str] = []
    index = 0
    length = len(text)
    in_string = False
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if char == "\\" and index + 1 < length:
                out.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < length:
            nxt = text[index + 1]
            if nxt == "/":
                while index < length and text[index] not in "\r\n":
                    index += 1
                continue
            if nxt == "*":
                end = text.find("*/", index + 2)
                if end < 0:
                    raise JsoncError("块注释没有闭合：缺少 */")
                index = end + 2
                continue
        out.append(char)
        index += 1
    return "".join(out)


def strip_trailing_commas(text: str) -> str:
    """去掉 ``}`` / ``]`` 前的尾逗号。"""
    out: list[str] = []
    index = 0
    length = len(text)
    in_string = False
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if char == "\\" and index + 1 < length:
                out.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == ",":
            look = index + 1
            while look < length and text[look] in " \t\r\n":
                look += 1
            if look < length and text[look] in "}]":
                index += 1
                continue
        out.append(char)
        index += 1
    return "".join(out)


def loads(text: str):
    """解析 JSONC 文本。"""
    cleaned = strip_trailing_commas(strip_comments(text))
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise JsoncError(f"配置解析失败（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}") from None


def load(path: str):
    """从文件读取 JSONC。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return loads(handle.read())
    except FileNotFoundError:
        raise JsoncError(f"配置文件不存在：{path}") from None
