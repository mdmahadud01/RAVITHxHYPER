import asyncio
import threading
import queue
import json
import time
import os
import hmac
from collections import deque
from datetime import datetime, timezone, timedelta
import pytz

from flask import Flask, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
from flask_sock import Sock
from pyquotex.stable_api import Quotex

import re
import traceback
from io import BytesIO
import urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None


# ==========================================
# EMBEDDED WEB UI (index.html) - served directly from this file
# Direct URL open korlei full UI (Login page shoho) load hobe.
# Kono extra HTML file ba template folder er dorkar nei.
# ==========================================
UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
    <title>HyperTrade — RAVITH AI PRO</title>

    <script src="https://cdn.tailwindcss.com">
    </script>
    <script src="https://unpkg.com/lucide@latest">
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet" />

    <style>
        :root {
            --bg: #f0f4fa;
            --text: #0f172a;
            --muted: #64748b;
            --primary: #16a34a;
            --red: #ef4444;
            --glass-alpha: 0.28;
            --glass-border-alpha: 0.45;
            --glass-bg-rgb: 255, 255, 255;
            --glass-border-rgb: 255, 255, 255;
            --speed-multiplier: 1;
            --anim-speed: 1;
            --glass-blur: 32px;
            --glass-opacity: 0.28;
            --indicator-glow: 0.08;
            --ui-scale: 1;
            --anim-smooth: cubic-bezier(0.22, 1, 0.36, 1);
            --anim-spring: cubic-bezier(0.34, 1.45, 0.64, 1);
            --font-base: 12px;
            --watermark-text: "𝐑𝐀𝐕𝐈𝐓𝐇 𝐒𝐒";
            --dashboard-name: "RAVITH PRO";
            --nav-idle: rgba(20, 24, 34, 0.72);
            --nav-active: #007aff;
        }

        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
            font-family: 'JetBrains Mono', monospace;
            margin: 0;
            padding: 0;
        }

        html {
            font-size: var(--font-base);
        }

        body {
            background: linear-gradient(165deg, #eef3fb 0%, #f5f8fc 40%, #f0f7f4 100%);
            color: var(--text);
            overflow-x: hidden;
            min-height: 100vh;
            transition: background 0.4s ease, color 0.4s ease;
            font-size: 1rem;
            padding-top: 48px;
            padding-bottom: calc(92px + env(safe-area-inset-bottom, 0px));
        }

        body.dark-mode {
            --bg: #06080c;
            --text: #f1f5f9;
            --muted: #94a3b8;
            --glass-alpha: 0.14;
            --glass-border-alpha: 0.16;
            --glass-bg-rgb: 12, 16, 24;
            --glass-border-rgb: 255, 255, 255;
            --nav-idle: rgba(242, 244, 248, 0.78);
            --nav-active: #389cff;
            background: #06080c;
        }

        .ambient {
            position: fixed;
            inset: 0;
            z-index: -2;
            pointer-events: none;
            background:
                radial-gradient(circle at 12% 18%, rgba(34, 197, 94, 0.09), transparent 42%),
                radial-gradient(circle at 88% 12%, rgba(59, 130, 246, 0.07), transparent 42%),
                radial-gradient(circle at 50% 88%, rgba(168, 85, 247, 0.05), transparent 45%);
        }

        #app-wrapper {
            min-height: 100vh;
            transition: filter calc(0.4s * var(--speed-multiplier)) var(--anim-smooth),
                transform calc(0.4s * var(--speed-multiplier)) var(--anim-smooth);
        }
        #app-wrapper.blur-active {
            filter: blur(8px) brightness(0.9);
            transform: scale(0.97);
            pointer-events: none;
        }

        main {
            position: relative;
            max-width: 850px;
            margin: 0 auto;
            padding: 16px 16px 20px;
            min-height: 100vh;
            overflow: hidden;
        }

        .view-container {
            position: absolute;
            top: 0;
            left: 16px;
            right: 16px;
            opacity: 0;
            pointer-events: none;
            transform: translateX(36px);
            transition: transform calc(0.5s * var(--anim-speed)) var(--anim-smooth),
                opacity calc(0.45s * var(--anim-speed)) var(--anim-smooth);
            will-change: transform, opacity;
        }
        .view-container.active {
            opacity: 1;
            pointer-events: auto;
            transform: translateX(0);
            position: relative;
            top: 0;
            left: 0;
            right: 0;
        }
        .view-container.exit-left {
            transform: translateX(-36px);
            opacity: 0;
        }
        .view-container.exit-right {
            transform: translateX(36px);
            opacity: 0;
        }

        .hyper-group {
            background: rgba(var(--glass-bg-rgb), var(--glass-opacity));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            border-radius: 20px;
            overflow: hidden;
            margin-bottom: 14px;
            backdrop-filter: blur(var(--glass-blur)) saturate(160%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(160%);
            box-shadow: none;
            transition: background 0.3s ease, border 0.3s ease;
        }
        body.dark-mode .hyper-group {
            background: rgba(14, 18, 28, 0.42);
            border-color: rgba(255,255,255,0.10);
            box-shadow: none;
        }

        .hyper-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            cursor: pointer;
            transition: background 0.2s ease;
            position: relative;
        }
        .hyper-item:not(:last-child)::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 16px;
            right: 16px;
            height: 1px;
            background: rgba(var(--glass-border-rgb), var(--glass-border-alpha));
        }
        .hyper-item:active {
            background: rgba(255, 255, 255, 0.1);
        }

        .item-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .item-icon {
            width: 28px;
            height: 28px;
            border-radius: 8px;
            background: rgba(22, 163, 74, 0.12);
            color: var(--primary);
            display: grid;
            place-items: center;
            font-size: 0.9rem;
        }
        .item-title {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text);
        }
        .item-subtitle {
            font-size: 0.65rem;
            color: var(--muted);
            margin-top: 2px;
        }
        .item-right {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .item-value {
            font-size: 0.75rem;
            color: var(--muted);
            font-weight: 500;
        }
        .item-arrow {
            color: rgba(15, 23, 42, 0.25);
        }
        body.dark-mode .item-arrow {
            color: rgba(255, 255, 255, 0.3);
        }

        .toggle {
            width: 46px;
            height: 28px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.16);
            border: 1px solid rgba(255, 255, 255, 0.45);
            position: relative;
            cursor: pointer;
            flex-shrink: 0;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            transition: background calc(0.35s * var(--anim-speed)) var(--anim-smooth),
                        border-color 0.3s ease;
        }
        .toggle::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 2px;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #ffffff;
            transform: translateY(-50%);
            transition: transform calc(0.4s * var(--speed-multiplier)) var(--anim-spring),
                        background 0.3s ease;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
        }
        .toggle:active::after {
            transform: translateY(-50%) scale(0.92);
        }
        .toggle.active {
            background: var(--primary);
            border-color: rgba(255, 255, 255, 0.2);
        }
        .toggle.active::after {
            transform: translateY(-50%) translateX(18px);
        }
        .toggle.active:active::after {
            transform: translateY(-50%) translateX(18px) scale(0.92);
        }
        body.dark-mode .toggle {
            background: rgba(255, 255, 255, 0.16);
            border-color: rgba(255, 255, 255, 0.14);
        }
        body.dark-mode .toggle.active {
            background: var(--primary);
            border-color: rgba(255, 255, 255, 0.22);
        }

        .signal-panel {
            text-align: center;
            padding: 20px 14px;
        }

        .chart-panel {
            position: relative;
            border-radius: 18px;
            overflow: hidden;
            background: linear-gradient(140deg, rgba(0, 18, 36, 0.72), rgba(5, 10, 20, 0.78));
            border: 1px solid rgba(0, 242, 254, 0.18);
            box-shadow: none;
            margin: 0 auto 12px;
            aspect-ratio: 16 / 9;
            width: 100%;
        }
        #chart {
            display: block;
            width: 100%;
            height: 100%;
            background: #050508;
            image-rendering: auto;
        }
        .chart-status {
            position: absolute;
            top: 8px;
            right: 10px;
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 3px 8px;
            border-radius: 10px;
            background: rgba(0, 242, 254, 0.12);
            border: 1px solid rgba(0, 242, 254, 0.35);
            color: #00F2FE;
            font-size: 0.55rem;
            letter-spacing: 1px;
            font-weight: 700;
            z-index: 3;
            backdrop-filter: blur(6px);
        }
        .chart-status .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #00F2FE;
            box-shadow: 0 0 6px #00F2FE;
            animation: pulse 1.5s infinite;
        }
        .chart-status.err {
            background: rgba(239, 68, 68, 0.15);
            border-color: rgba(239, 68, 68, 0.5);
            color: #ff6688;
        }
        .chart-status.err .dot {
            background: #ff3366;
            box-shadow: 0 0 6px #ff3366;
        }
        .chart-status.warn {
            background: rgba(255, 204, 0, 0.15);
            border-color: rgba(255, 204, 0, 0.5);
            color: #FFCC00;
        }
        .chart-status.warn .dot {
            background: #FFCC00;
            box-shadow: 0 0 6px #FFCC00;
        }

        .signal-card {
            margin: 0 auto 14px;
            padding: 14px 12px;
            border-radius: 16px;
            background: rgba(var(--glass-bg-rgb), var(--glass-opacity));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            box-shadow: none;
            text-align: left;
            font-size: 0.72rem;
            line-height: 1.65;
            white-space: pre;
            overflow-x: auto;
            color: var(--text);
            display: none;
            font-family: 'JetBrains Mono', monospace;
        }
        .signal-card.show {
            display: block;
            animation: cardIn calc(0.4s * var(--speed-multiplier)) var(--anim-spring);
        }
        @keyframes cardIn {
            from {
                opacity: 0;
                transform: translateY(10px) scale(0.97);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        .result-card {
            margin: 0 auto 14px;
            padding: 14px 12px;
            border-radius: 16px;
            background: rgba(var(--glass-bg-rgb), var(--glass-opacity));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            box-shadow: none;
            text-align: left;
            font-size: 0.72rem;
            line-height: 1.65;
            white-space: pre;
            overflow-x: auto;
            color: var(--text);
            display: none;
            font-family: 'JetBrains Mono', monospace;
        }
        .result-card.show {
            display: block;
            animation: cardIn calc(0.4s * var(--speed-multiplier)) var(--anim-spring);
        }
        .result-card.win {
            border-color: rgba(34, 197, 94, 0.5);
            background: rgba(34, 197, 94, 0.08);
        }
        .result-card.loss {
            border-color: rgba(239, 68, 68, 0.5);
            background: rgba(239, 68, 68, 0.08);
        }

        .action-row {
            display: flex;
            gap: 8px;
            width: 100%;
            flex-wrap: wrap;
        }
        .action-row .btn-primary {
            flex: 1;
            min-width: 120px;
        }
        .action-row .btn-secondary {
            flex: 1;
            min-width: 100px;
        }
        .action-row .btn-partial {
            flex: 1;
            min-width: 120px;
            background: linear-gradient(135deg, #8b5cf6, #6d28d9);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 14px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: none;
            letter-spacing: 0.5px;
        }
        .action-row .btn-partial:active {
            transform: scale(0.96);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 16px;
        }
        .stat-card {
            background: rgba(var(--glass-bg-rgb), var(--glass-opacity));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            border-radius: 16px;
            padding: 10px 4px;
            text-align: center;
            backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            box-shadow: none;
        }
        .stat-card strong {
            display: block;
            font-size: 1rem;
            font-weight: 700;
            color: var(--text);
            margin-top: 4px;
        }
        .stat-card span {
            font-size: 0.55rem;
            color: var(--muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .section-label {
            margin: 18px 4px 8px;
            font-size: 0.65rem;
            letter-spacing: 2px;
            color: var(--muted);
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .two-col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }
        .two-col .hyper-group {
            margin-bottom: 0;
        }
        .two-col .hyper-item {
            padding: 10px 12px;
        }
        .two-col .hyper-item:not(:last-child)::after {
            display: none;
        }
        .two-col .item-value {
            background: rgba(255, 255, 255, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.5);
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.65rem;
            font-weight: 600;
            color: var(--text);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 90px;
            text-align: center;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: none;
        }
        body.dark-mode .two-col .item-value {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #f1f5f9;
        }

        .overlay {
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.3);
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: opacity calc(0.3s * var(--speed-multiplier)) ease;
        }
        .overlay.show {
            opacity: 1;
            pointer-events: auto;
        }

        .hyper-dialog {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) scale(0.96);
            width: 85%;
            max-width: 340px;
            background: rgba(var(--glass-bg-rgb), calc(var(--glass-opacity) + 0.15));
            backdrop-filter: blur(var(--glass-blur)) saturate(160%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(160%);
            border: 1px solid rgba(var(--glass-border-rgb), calc(var(--glass-border-alpha) + 0.15));
            border-radius: 20px;
            z-index: 1001;
            opacity: 0;
            pointer-events: none;
            transition: all calc(0.35s * var(--anim-speed)) var(--anim-smooth);
            overflow: hidden;
            box-shadow: none;
        }
        .hyper-dialog.show {
            opacity: 1;
            pointer-events: auto;
        }
        .hyper-dialog.anim-scale {
            transform: translate(-50%, -50%) scale(0.85);
        }
        .hyper-dialog.anim-scale.show {
            transform: translate(-50%, -50%) scale(1);
        }
        .hyper-dialog.anim-fade {
            transform: translate(-50%, -50%);
        }
        .hyper-dialog.anim-fade.show {
            opacity: 1;
        }
        .hyper-dialog.anim-slide-up {
            transform: translate(-50%, 100%);
        }
        .hyper-dialog.anim-slide-up.show {
            transform: translate(-50%, -50%);
        }
        .hyper-dialog.anim-flip {
            transform: translate(-50%, -50%) rotateX(-90deg);
        }
        .hyper-dialog.anim-flip.show {
            transform: translate(-50%, -50%) rotateX(0);
        }
        .hyper-dialog.anim-bounce {
            transform: translate(-50%, -50%) scale(0.5);
        }
        .hyper-dialog.anim-bounce.show {
            transform: translate(-50%, -50%) scale(1);
        }

        .dialog-title {
            text-align: center;
            padding: 14px 14px 6px;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--muted);
            letter-spacing: 1px;
        }
        .dialog-list {
            padding: 6px;
            max-height: 55vh;
            overflow-y: auto;
            -webkit-overflow-scrolling: touch;
        }
        .dialog-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            border-radius: 10px;
            cursor: pointer;
            transition: 0.2s ease;
        }
        .dialog-item:active {
            background: rgba(255, 255, 255, 0.1);
            transform: scale(0.98);
        }
        .dialog-item .check-icon {
            color: var(--primary);
            opacity: 0;
            transform: scale(0.5);
            transition: 0.3s var(--anim-spring);
        }
        .dialog-item.selected {
            background: rgba(34, 197, 94, 0.15);
        }
        .dialog-item.selected .check-icon {
            opacity: 1;
            transform: scale(1);
        }
        .dialog-item span {
            font-size: 0.7rem;
            font-weight: 500;
        }
        .dialog-item .check-box {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid var(--muted);
            display: grid;
            place-items: center;
            transition: 0.2s ease;
            flex-shrink: 0;
        }
        .dialog-item .check-box.checked {
            background: var(--primary);
            border-color: var(--primary);
        }
        .dialog-item .check-box.checked::after {
            content: '✓';
            color: white;
            font-size: 0.6rem;
            font-weight: bold;
        }

        .header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 48px;
            z-index: 50;
            background: rgba(var(--glass-bg-rgb), calc(var(--glass-opacity) + 0.12));
            backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(150%);
            border-bottom: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            box-shadow: none;
            transition: background 0.3s ease, border 0.3s ease;
            display: flex;
            align-items: center;
        }
        .header-inner {
            max-width: 850px;
            margin: 0 auto;
            width: 100%;
            height: 100%;
            padding: 0 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .brand-logo {
            width: 24px;
            height: 24px;
            border-radius: 6px;
            background: linear-gradient(135deg, #22c55e, #16a34a);
            display: grid;
            place-items: center;
            color: white;
            box-shadow: none;
            flex-shrink: 0;
        }
        .header-title {
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: var(--text);
            white-space: nowrap;
        }
        .header-title span {
            color: var(--primary);
        }
        .live-badge {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            background: rgba(var(--glass-bg-rgb), calc(var(--glass-opacity) + 0.1));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            border-radius: 12px;
            font-size: 0.55rem;
            font-weight: 600;
            color: var(--muted);
            flex-shrink: 0;
            box-shadow: none;
        }
        .pulse-dot {
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4);
            }
            70% {
                box-shadow: 0 0 0 6px rgba(34, 197, 94, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
            }
        }

        .user-count-badge {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            background: rgba(59, 130, 246, 0.12);
            border: 1px solid rgba(59, 130, 246, 0.35);
            border-radius: 12px;
            font-size: 0.55rem;
            font-weight: 700;
            color: #2563eb;
            flex-shrink: 0;
        }
        body.dark-mode .user-count-badge {
            color: #93c5fd;
            background: rgba(59, 130, 246, 0.18);
            border-color: rgba(59, 130, 246, 0.45);
        }

        .credit-badge {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            background: rgba(255, 204, 0, 0.12);
            border: 1px solid rgba(255, 204, 0, 0.35);
            border-radius: 12px;
            font-size: 0.55rem;
            font-weight: 700;
            color: #d97706;
            flex-shrink: 0;
        }
        .credit-badge.pro {
            background: rgba(139, 92, 246, 0.12);
            border-color: rgba(139, 92, 246, 0.35);
            color: #7c3aed;
        }

        /* ==================================================================
           iOS 27 LIQUID GLASS DOCK (ported from NAVIGATION.html)
           Pill tabs + optical droplet + lens + separate Profile button
           Flat glass: no outer drop shadows, only rim highlights.
           ================================================================== */
        .dock-container {
            position: fixed;
            bottom: calc(14px + env(safe-area-inset-bottom, 0px));
            left: 50%;
            transform: translateX(-50%);
            width: min(calc(100% - 28px), 410px);
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 50;
        }
        .glass-pill,
        .glass-action-btn {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.75);
            box-shadow: inset 0 1.5px 1.5px rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(var(--glass-blur)) saturate(210%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(210%);
            transition: background 0.3s ease, border-color 0.3s ease,
                        box-shadow 0.3s ease, transform 0.2s ease, color 0.16s ease;
        }
        body.dark-mode .glass-pill,
        body.dark-mode .glass-action-btn {
            background: rgba(26, 28, 34, 0.62);
            border-color: rgba(255, 255, 255, 0.14);
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.28);
        }
        .liquid-nav {
            position: relative;
            flex: 1;
            height: 52px;
            padding: 5px;
            border-radius: 999px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            align-items: center;
            touch-action: none;
            cursor: grab;
            outline: none;
            -webkit-user-select: none;
            user-select: none;
        }
        .liquid-nav:active { cursor: grabbing; }
        .liquid-nav:focus-visible {
            box-shadow: inset 0 1.5px 1.5px rgba(255, 255, 255, 0.95), 0 0 0 2px var(--nav-active);
        }
        .nav-tab {
            position: relative;
            z-index: 2;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 3px;
            color: var(--nav-idle);
            pointer-events: none;
            transition: color 0.16s ease, opacity 0.16s ease;
        }
        .nav-tab.active { color: var(--nav-active); }
        .nav-tab svg { width: 19px; height: 19px; display: block; }
        .nav-tab span {
            font-size: 9.5px;
            font-weight: 600;
            letter-spacing: -0.01em;
            white-space: nowrap;
        }
        .liquid-nav.is-interacting .nav-tab.under-lens { opacity: 0.16; }
        .glass-droplet {
            position: absolute;
            top: 5px;
            left: 5px;
            height: calc(100% - 10px);
            width: 0;
            border-radius: 999px;
            z-index: 4;
            pointer-events: none;
            overflow: hidden;
            background: rgba(0, 122, 255, 0.12);
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.85);
            transform-origin: center center;
            will-change: transform;
            transition: background 0.2s ease, box-shadow 0.2s ease;
        }
        body.dark-mode .glass-droplet {
            background: rgba(255, 255, 255, 0.13);
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.22);
        }
        .glass-droplet.is-magnified {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(240, 248, 255, 0.45) 50%, rgba(255, 255, 255, 0.85) 100%);
            box-shadow:
                0 0 18px rgba(0, 122, 255, calc(var(--indicator-glow) + 0.08)),
                inset 0 2px 2.5px rgba(255, 255, 255, 1),
                inset 0 -1.5px 2px rgba(255, 255, 255, 0.85),
                inset 2px 0 4px rgba(80, 180, 255, 0.5),
                inset -2px 0 4px rgba(245, 150, 210, 0.4);
            backdrop-filter: blur(10px) saturate(225%);
            -webkit-backdrop-filter: blur(10px) saturate(225%);
        }
        body.dark-mode .glass-droplet.is-magnified {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.28) 0%, rgba(255, 255, 255, 0.06) 50%, rgba(255, 255, 255, 0.18) 100%);
            box-shadow:
                0 0 20px rgba(56, 156, 255, calc(var(--indicator-glow) + 0.1)),
                inset 0 1.5px 2px rgba(255, 255, 255, 0.85),
                inset 0 -1.5px 2px rgba(255, 255, 255, 0.4),
                inset 2px 0 4px rgba(110, 205, 255, 0.5),
                inset -2px 0 4px rgba(215, 145, 255, 0.35);
        }
        .lens-track {
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            align-items: center;
            opacity: 0;
            transition: opacity 0.14s ease;
            will-change: transform;
        }
        .glass-droplet.is-magnified .lens-track { opacity: 1; }
        .lens-tab {
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 3px;
            color: var(--nav-idle);
            transform: scale(1.16);
        }
        .lens-tab.active { color: var(--nav-active); }
        .lens-tab svg { width: 19px; height: 19px; display: block; }
        .lens-tab span {
            font-size: 9.5px;
            font-weight: 700;
            letter-spacing: -0.01em;
            white-space: nowrap;
        }
        .glass-action-btn {
            width: 52px;
            height: 52px;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--nav-idle);
            cursor: pointer;
            flex-shrink: 0;
            -webkit-appearance: none;
            appearance: none;
            font: inherit;
            outline: none;
            padding: 0;
        }
        .glass-action-btn:hover { background: rgba(255, 255, 255, 0.82); }
        body.dark-mode .glass-action-btn:hover { background: rgba(34, 37, 45, 0.72); }
        .glass-action-btn:active { transform: scale(0.92); }
        .glass-action-btn.is-active {
            color: var(--nav-active);
            transform: scale(0.94);
        }
        .glass-action-btn:focus-visible {
            box-shadow: inset 0 1.5px 1.5px rgba(255, 255, 255, 0.95), 0 0 0 2px var(--nav-active);
        }
        .glass-action-btn svg { width: 23px; height: 23px; }

        /* ==================================================================
           SELECTION DIALOG — DRAGGABLE ZOOM INDICATOR (nav-bar style droplet)
           ================================================================== */
        #dialogList {
            position: relative;
        }
        .dialog-droplet {
            position: absolute;
            left: 4px;
            width: calc(100% - 8px);
            border-radius: 12px;
            background: rgba(34, 197, 94, 0.14);
            border: 1px solid rgba(34, 197, 94, 0.22);
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.6);
            z-index: 0;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease, transform 0.38s var(--anim-spring), background 0.2s ease, border-color 0.2s ease;
            will-change: transform;
            transform-origin: center center;
        }
        .dialog-droplet.is-zoomed {
            background: rgba(34, 197, 94, 0.2);
            border-color: rgba(34, 197, 94, 0.35);
        }
        .dialog-item {
            position: relative;
            z-index: 1;
            transition: transform 0.16s var(--anim-spring), background 0.2s ease;
        }

        /* ==================================================================
           PAGE-END SPRING BOUNCE + EXTRA COMPACT NAV
           ================================================================== */
        @keyframes pageBounceBottom {
            0% { transform: translateY(0); }
            30% { transform: translateY(9px); }
            55% { transform: translateY(-4px); }
            78% { transform: translateY(2px); }
            100% { transform: translateY(0); }
        }
        @keyframes pageBounceTop {
            0% { transform: translateY(0); }
            30% { transform: translateY(-9px); }
            55% { transform: translateY(4px); }
            78% { transform: translateY(-2px); }
            100% { transform: translateY(0); }
        }
        body.nav-compact .liquid-nav { height: 44px; }
        body.nav-compact .glass-action-btn { width: 44px; height: 44px; }
        body.nav-compact .nav-tab svg,
        body.nav-compact .lens-tab svg { width: 16px; height: 16px; }
        body.nav-compact .nav-tab span,
        body.nav-compact .lens-tab span { font-size: 8.5px; }
        body.nav-compact .dock-container { bottom: calc(10px + env(safe-area-inset-bottom, 0px)); }

        /* Reduced motion support */
        @media (prefers-reduced-motion: reduce) {
            .view-container,
            .view-container.active {
                transition: opacity 0.2s ease !important;
                transform: none !important;
            }
            .glass-droplet,
            .lens-track,
            .toggle,
            .toggle::after,
            input[type="range"]::-webkit-slider-thumb {
                transition-duration: 0.01s !important;
            }
            #app-wrapper {
                animation: none !important;
            }
        }

        .btn-primary {
            width: 100%;
            padding: 12px;
            border-radius: 14px;
            background: linear-gradient(135deg, #22c55e, #16a34a);
            color: white;
            font-size: 0.8rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: transform 0.2s ease, opacity 0.2s ease;
            box-shadow: none;
            letter-spacing: 1px;
        }
        .btn-primary:active {
            transform: scale(0.97);
        }
        .btn-primary.waiting {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            box-shadow: none;
            cursor: default;
        }
        .btn-primary.mtg {
            background: linear-gradient(135deg, #8b5cf6, #6d28d9);
            box-shadow: none;
            cursor: default;
        }
        .btn-primary.analyzing {
            background: linear-gradient(135deg, #06b6d4, #0891b2);
            box-shadow: none;
            cursor: default;
        }
        .btn-primary.scanning {
            background: linear-gradient(135deg, #f472b6, #ec4899);
            box-shadow: none;
            cursor: default;
        }
        .btn-primary.auto-active {
            background: linear-gradient(135deg, #a78bfa, #7c3aed);
            box-shadow: none;
        }
        .btn-primary.no-credit {
            background: linear-gradient(135deg, #6b7280, #4b5563);
            box-shadow: none;
            cursor: not-allowed;
        }

        .btn-secondary {
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s ease;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        .btn-secondary:active {
            transform: scale(0.96);
            background: rgba(239, 68, 68, 0.2);
        }

        .profile-avatar {
            width: 60px;
            height: 60px;
            margin: 0 auto 10px;
            border-radius: 50%;
            background: rgba(22, 163, 74, 0.12);
            border: 2px solid rgba(22, 163, 74, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary);
        }

        .uid-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 12px;
            cursor: pointer;
            background: rgba(var(--glass-bg-rgb), 0.5);
            border: 1px solid rgba(var(--glass-border-rgb), 0.6);
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--muted);
            transition: 0.2s ease;
            margin-top: 6px;
        }
        .uid-badge:active {
            transform: scale(0.96);
            background: rgba(var(--glass-bg-rgb), 0.7);
        }
        .uid-badge .copy-hint {
            font-size: 0.55rem;
            color: var(--primary);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .uid-badge.copied .copy-hint {
            opacity: 1;
        }

        .profile-credit-box {
            margin: 16px auto;
            padding: 14px;
            border-radius: 16px;
            background: rgba(var(--glass-bg-rgb), calc(var(--glass-alpha) + 0.05));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            backdrop-filter: blur(18px);
            text-align: center;
        }
        .profile-credit-box .credit-label {
            font-size: 0.6rem;
            color: var(--muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .profile-credit-box .credit-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
            margin-top: 4px;
        }
        .profile-credit-box .credit-type {
            font-size: 0.6rem;
            padding: 3px 10px;
            border-radius: 8px;
            display: inline-block;
            margin-top: 6px;
            font-weight: 600;
        }
        .profile-credit-box .credit-type.free {
            background: rgba(245, 158, 11, 0.15);
            color: #d97706;
        }
        .profile-credit-box .credit-type.pro {
            background: rgba(139, 92, 246, 0.15);
            color: #7c3aed;
        }

        .btn-logout {
            margin: 16px auto;
            display: block;
            padding: 12px 30px;
            border-radius: 14px;
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s ease;
            letter-spacing: 0.5px;
        }
        .btn-logout:active {
            transform: scale(0.96);
            background: rgba(239, 68, 68, 0.2);
        }

        input[type="range"] {
            -webkit-appearance: none;
            appearance: none;
            width: 100%;
            height: 4px;
            border-radius: 999px;
            outline: none;
            cursor: pointer;
            background: linear-gradient(to right, var(--primary) var(--fill, 50%), rgba(15, 23, 42, 0.15) var(--fill, 50%));
            transition: height 0.15s ease;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #ffffff;
            border: 0.5px solid rgba(0, 0, 0, 0.04);
            cursor: pointer;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.22);
            transition: transform 0.15s var(--anim-smooth);
        }
        input[type="range"]:active::-webkit-slider-thumb {
            transform: scale(1.14);
        }
        body.dark-mode input[type="range"] {
            background: linear-gradient(to right, var(--primary) var(--fill, 50%), rgba(255, 255, 255, 0.18) var(--fill, 50%));
        }
        .slider-group {
            display: flex;
            align-items: center;
            gap: 6px;
            flex: 1;
            min-width: 0;
        }
        .slider-group span {
            min-width: 36px;
            text-align: center;
            font-size: 0.65rem;
            color: var(--muted);
        }

        .telegram-input {
            background: rgba(var(--glass-bg-rgb), 0.5);
            border: 1px solid rgba(var(--glass-border-rgb), 0.6);
            border-radius: 10px;
            padding: 6px 10px;
            font-size: 0.7rem;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text);
            width: 100%;
            max-width: 220px;
            outline: none;
            transition: border 0.2s ease;
        }
        .telegram-input:focus {
            border-color: var(--primary);
        }
        body.dark-mode .telegram-input {
            background: rgba(255, 255, 255, 0.05);
            color: #f1f5f9;
        }

        .tg-status {
            font-size: 0.6rem;
            color: var(--muted);
            text-align: center;
            padding: 4px 0;
            min-height: 18px;
        }
        .tg-status.success {
            color: #22c55e;
        }
        .tg-status.error {
            color: #ef4444;
        }
        .tg-status.sending {
            color: #06b6d4;
        }

        .auto-status-bar {
            margin: 0 auto 14px;
            padding: 10px 14px;
            border-radius: 14px;
            background: rgba(124, 58, 237, 0.08);
            border: 1px solid rgba(124, 58, 237, 0.3);
            font-size: 0.65rem;
            color: var(--muted);
            text-align: center;
            display: none;
            line-height: 1.6;
        }
        .auto-status-bar.show {
            display: block;
            animation: cardIn 0.3s var(--anim-spring);
        }
        .auto-status-bar .scanning-text {
            color: #a78bfa;
            font-weight: 600;
        }
        .auto-status-bar .signal-found {
            color: #22c55e;
            font-weight: 700;
        }
        .auto-status-bar .no-signal {
            color: #f59e0b;
            font-weight: 600;
        }

        ::-webkit-scrollbar {
            width: 0px;
            background: transparent;
        }

        .watermark-preview {
            font-size: 1.2rem;
            padding: 8px 12px;
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.05);
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 1px;
            color: var(--muted);
        }
        body.dark-mode .watermark-preview {
            background: rgba(255, 255, 255, 0.05);
        }

        .auth-overlay {
            position: fixed;
            inset: 0;
            z-index: 2000;
            background: rgba(var(--glass-bg-rgb), 0.85);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.4s ease, visibility 0.4s ease;
            opacity: 0;
            visibility: hidden;
        }
        .auth-overlay.visible {
            opacity: 1;
            visibility: visible;
        }
        .auth-box {
            background: rgba(var(--glass-bg-rgb), calc(var(--glass-opacity) + 0.2));
            border: 1px solid rgba(var(--glass-border-rgb), calc(var(--glass-border-alpha) + 0.2));
            border-radius: 22px;
            padding: 30px 24px;
            max-width: 400px;
            width: 90%;
            box-shadow: none;
            backdrop-filter: blur(var(--glass-blur)) saturate(160%);
            -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(160%);
            max-height: 90vh;
            overflow-y: auto;
        }
        .auth-box .logo {
            text-align: center;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 20px;
        }
        .auth-box .logo span {
            color: var(--text);
        }
        .auth-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            border-bottom: 2px solid rgba(var(--glass-border-rgb), 0.3);
            padding-bottom: 8px;
        }
        .auth-tab {
            flex: 1;
            padding: 8px;
            text-align: center;
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--muted);
            cursor: pointer;
            border-radius: 8px;
            transition: 0.2s ease;
            border: none;
            background: transparent;
        }
        .auth-tab.active {
            color: var(--text);
            background: rgba(var(--glass-bg-rgb), 0.2);
            border-bottom: 2px solid var(--primary);
        }
        .auth-form {
            display: none;
            flex-direction: column;
            gap: 14px;
        }
        .auth-form.active {
            display: flex;
        }
        .auth-form label {
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--muted);
            letter-spacing: 0.5px;
        }
        .auth-form input {
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid rgba(var(--glass-border-rgb), 0.6);
            background: rgba(var(--glass-bg-rgb), 0.5);
            font-size: 0.8rem;
            color: var(--text);
            outline: none;
            transition: border 0.2s ease;
            font-family: 'JetBrains Mono', monospace;
        }
        .auth-form input:focus {
            border-color: var(--primary);
        }
        .auth-form .btn-auth {
            padding: 12px;
            border-radius: 12px;
            border: none;
            font-weight: 600;
            font-size: 0.8rem;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            background: linear-gradient(135deg, #22c55e, #16a34a);
            color: white;
            box-shadow: none;
        }
        .auth-form .btn-auth:active {
            transform: scale(0.96);
        }
        .auth-form .btn-auth.secondary {
            background: linear-gradient(135deg, #8b5cf6, #6d28d9);
            box-shadow: none;
        }
        .auth-form .btn-auth:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .auth-form .auth-error {
            color: #ef4444;
            font-size: 0.7rem;
            text-align: center;
            min-height: 18px;
        }
        .auth-form .auth-success {
            color: #22c55e;
            font-size: 0.7rem;
            text-align: center;
            min-height: 18px;
        }
        .auth-form .otp-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .auth-form .otp-row input {
            flex: 1;
        }
        .auth-form .otp-row .btn-otp {
            padding: 10px 14px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            font-size: 0.7rem;
            cursor: pointer;
            background: rgba(139, 92, 246, 0.15);
            color: #7c3aed;
            transition: 0.2s ease;
            white-space: nowrap;
        }
        .auth-form .otp-row .btn-otp:active {
            transform: scale(0.96);
        }
        .auth-form .otp-row .btn-otp:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .auth-form .switch-link {
            text-align: center;
            font-size: 0.7rem;
            color: var(--muted);
            cursor: pointer;
            transition: 0.2s ease;
        }
        .auth-form .switch-link:hover {
            color: var(--primary);
        }
        .auth-form .otp-timer {
            font-size: 0.65rem;
            color: var(--muted);
            text-align: center;
        }
        .auth-footer {
            text-align: center;
            margin-top: 16px;
            font-size: 0.6rem;
            color: var(--muted);
        }
        body.dark-mode .auth-overlay {
            background: rgba(15, 23, 42, 0.9);
        }
        body.dark-mode .auth-box {
            background: rgba(15, 23, 42, 0.95);
            border-color: rgba(255, 255, 255, 0.1);
        }
        body.dark-mode .auth-form input {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.15);
            color: #f1f5f9;
        }

        .toast {
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            padding: 8px 18px;
            border-radius: 12px;
            background: rgba(34, 197, 94, 0.9);
            color: white;
            font-size: 0.7rem;
            font-weight: 600;
            z-index: 3000;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }
        .toast.show {
            opacity: 1;
        }

        /* Full chart elements always visible */
        .chart-panel .chart-status {
            opacity: 1;
        }
        .chart-panel .chart-status .dot {
            opacity: 1;
        }

        .fc-hero { text-align: center; padding: 14px 6px 6px; }
        .fc-hero h3 { font-size: 1.02rem; font-weight: 800; background: linear-gradient(90deg, #22c55e, #00f2fe);
            -webkit-background-clip: text; background-clip: text; color: transparent; margin-bottom: 4px; }
        .fc-hero p { font-size: 0.58rem; color: var(--muted); }
        .fc-card { border-radius: 18px; padding: 14px 12px; margin-top: 12px;
            background: rgba(var(--glass-bg-rgb), var(--glass-alpha));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha)); backdrop-filter: blur(18px); }
        .fc-sec { font-size: 0.56rem; font-weight: 800; letter-spacing: 0.14em; color: var(--muted);
            text-transform: uppercase; margin: 12px 0 6px; }
        .fc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
        .fc-chip { display: flex; flex-direction: column; gap: 3px; padding: 8px 10px; border-radius: 13px; cursor: pointer;
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); }
        .fc-chip:active { transform: scale(0.96); }
        .fc-chip-l { font-size: 0.52rem; font-weight: 700; color: var(--muted); }
        .fc-chip-v { font-size: 0.66rem; font-weight: 700; color: #00f2fe; display: flex; align-items: center; justify-content: space-between; gap: 4px; }
        .fc-textarea { width: 100%; min-height: 118px; border-radius: 13px; padding: 10px 12px; resize: vertical;
            background: rgba(var(--glass-bg-rgb), 0.5); border: 1px solid rgba(var(--glass-border-rgb), 0.6);
            color: var(--text); font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; outline: none; box-sizing: border-box; }
        .fc-textarea:focus { border-color: rgba(0, 242, 254, 0.5); }
        .fc-run-btn { width: 100%; margin-top: 12px; padding: 11px 0; border: none; border-radius: 14px; cursor: pointer;
            background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; font-weight: 700; font-size: 0.75rem;
            letter-spacing: 1px; font-family: 'JetBrains Mono', monospace; }
        .fc-run-btn:disabled { opacity: 0.55; cursor: wait; }
        .fc-run-btn:active { transform: scale(0.98); }
        .fc-result-card { margin-top: 12px; border-radius: 16px; padding: 12px; white-space: pre-wrap;
            background: rgba(var(--glass-bg-rgb), calc(var(--glass-alpha)+0.05));
            border: 1px solid rgba(var(--glass-border-rgb), var(--glass-border-alpha));
            font-size: 0.68rem; line-height: 1.55; color: var(--text); font-family: 'JetBrains Mono', monospace; display: none; }
        .fc-result-card.show { display: block; }
        .fc-chip-stat { flex: 1; text-align: center; padding: 8px 4px; border-radius: 12px; background: rgba(255,255,255,0.05); }
        .fc-chip-stat strong { display: block; font-size: 0.85rem; font-weight: 800; }
        .fc-chip-stat span { font-size: 0.5rem; font-weight: 700; color: var(--muted); text-transform: uppercase; }
        .fc-status { margin-top: 10px; text-align: center; font-size: 0.6rem; font-weight: 700; min-height: 14px; color: var(--muted); }

    </style>
</head>
<body>

    <div class="ambient"></div>
    <div class="toast" id="toast"></div>

    <!-- AUTH OVERLAY -->
    <div class="auth-overlay visible" id="authOverlay">
        <div class="auth-box">
            <div class="logo">Hyper<span>Trade</span></div>

            <form class="auth-form active" id="gateForm" onsubmit="handleLogin(); return false;">
                <label>Password</label>
                <input type="password" id="gatePassword" placeholder="••••••••" autocomplete="current-password" required />
                <div class="auth-error" id="loginError"></div>
                <button class="btn-auth" id="loginBtn" onclick="handleLogin()">Unlock</button>
            </form>
            <div class="auth-footer">© 2026 RAVITH TRADING • Secure Access</div>
        </div>
    </div>

    <!-- MAIN APP -->    <!-- MAIN APP -->
    <header class="header">
        <div class="header-inner">
            <div style="display:flex;align-items:center;gap:8px;">
                <div class="brand-logo"><i data-lucide="activity" class="w-4 h-4"></i></div>
                <div class="header-title">Hyper<span>Trade</span></div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
                <div class="user-count-badge" id="userCountBadge"><i data-lucide="users" class="w-3 h-3"></i><span id="userCountText">0</span></div>
                <div class="live-badge"><span class="pulse-dot"></span> LIVE</div>
                <div class="credit-badge" id="headerCreditBadge">⚡ --</div>
            </div>
        </div>
    </header>

    <div class="overlay" id="overlay" onclick="closeDialog()"></div>
    <div class="hyper-dialog" id="selectionDialog">
        <div class="dialog-title" id="dialogTitle">Select Option</div>
        <div class="dialog-list" id="dialogList"></div>
    </div>

    <div id="app-wrapper">
        <main>
            <!-- HOME / ENGINE VIEW -->
            <div id="view-0" class="view-container active">
                <div class="hyper-group signal-panel">
                    <div class="chart-panel" id="chartPanel">
                        <div class="chart-status" id="chartStatus">
                            <span class="dot"></span>
                            <span id="chartStatusText">LIVE</span>
                        </div>
                        <canvas id="chart"></canvas>
                    </div>

                    <div class="auto-status-bar" id="autoStatusBar">
                        <span id="autoStatusText">SCANNING MARKETS...</span>
                    </div>

                    <pre class="signal-card" id="signalCard"></pre>
                    <pre class="result-card" id="resultCard"></pre>
                    <div class="tg-status" id="tgStatus"></div>

                    <div class="action-row">
                        <button class="btn-primary" id="actionBtn" onclick="onActionClick()">GENERATE SIGNAL</button>
                        <button class="btn-secondary" onclick="resetResult()">RESET</button>
                        <button class="btn-partial" onclick="sendPartialResult()">PARTIAL RESULT</button>
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card"><span>Wins</span><strong id="statWin">0</strong></div>
                    <div class="stat-card"><span>Losses</span><strong id="statLoss">0</strong></div>
                    <div class="stat-card"><span>Win Rate</span><strong id="statRate">--%</strong></div>
                </div>

                <div class="section-label">⚡ Market Configuration</div>

                <div class="two-col">
                    <div class="hyper-group">
                        <div class="hyper-item" onclick="openDialog('market')">
                            <div class="item-left">
                                <div class="item-icon"><i data-lucide="candlestick-chart" class="w-4 h-4"></i></div>
                                <div><div class="item-title">Market</div></div>
                            </div>
                            <div class="item-right">
                                <span class="item-value" id="val-market">USDBDT-OTC</span>
                                <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                            </div>
                        </div>
                    </div>
                    <div class="hyper-group">
                        <div class="hyper-item" onclick="openDialog('timeframe')">
                            <div class="item-left">
                                <div class="item-icon"><i data-lucide="clock" class="w-4 h-4"></i></div>
                                <div><div class="item-title">Time</div></div>
                            </div>
                            <div class="item-right">
                                <span class="item-value" id="val-timeframe">1 Minute</span>
                                <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="section-label">🧠 Strategy & Mode</div>

                <div class="hyper-group">
                    <div class="hyper-item" onclick="openDialog('signalMode')">
                        <div class="item-left">
                            <div class="item-icon" style="background:rgba(124,58,237,0.12);color:#7c3aed;">
                                <i data-lucide="radio" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <div class="item-title">Signal Mode</div>
                                <div class="item-subtitle">Manual or Auto</div>
                            </div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-signalMode">Manual</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                    <div class="hyper-item" onclick="openDialog('strategy')">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="brain-circuit" class="w-4 h-4"></i></div>
                            <div>
                                <div class="item-title">Strategy</div>
                                <div class="item-subtitle">Signal engine</div>
                            </div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-strategy">AI Smart Signal</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                    <div class="hyper-item" onclick="openDialog('chartType')">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="bar-chart-3" class="w-4 h-4"></i></div>
                            <div>
                                <div class="item-title">Chart</div>
                                <div class="item-subtitle">Visualisation</div>
                            </div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-chartType">Candlestick</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                    <div class="hyper-item" onclick="openDialog('chartStyle')">
                        <div class="item-left">
                            <div class="item-icon" style="background:rgba(0,242,254,0.12);color:#00F2FE;">
                                <i data-lucide="palette" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <div class="item-title">Chart Style</div>
                                <div class="item-subtitle">26 photo designs</div>
                            </div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-chartStyle">Style 1 - Classic</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                    <div class="hyper-item" id="autoMarketsItem" onclick="openDialog('autoMarkets')" style="display:none;">
                        <div class="item-left">
                            <div class="item-icon" style="background:rgba(236,72,153,0.12);color:#ec4899;">
                                <i data-lucide="globe" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <div class="item-title">Auto Markets</div>
                                <div class="item-subtitle">Select markets to scan</div>
                            </div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-autoMarkets">All</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                    <div class="hyper-item" onclick="toggleSwitch(this)">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="bell" class="w-4 h-4"></i></div>
                            <div>
                                <div class="item-title">Sound Alerts</div>
                                <div class="item-subtitle">Notify on signal</div>
                            </div>
                        </div>
                        <div class="item-right"><div class="toggle active" data-toggle-key="soundAlerts"></div></div>
                    </div>
                    <div class="hyper-item" onclick="toggleSwitch(this)">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="smartphone" class="w-4 h-4"></i></div>
                            <div>
                                <div class="item-title">Vibration</div>
                                <div class="item-subtitle">Haptic</div>
                            </div>
                        </div>
                        <div class="item-right"><div class="toggle active" data-toggle-key="vibration"></div></div>
                    </div>
                </div>
            </div>

            <!-- SETTINGS VIEW -->
            <div id="view-1" class="view-container">
                <div class="section-label">📡 Telegram Bot</div>
                <div class="hyper-group">
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon" style="background:rgba(0,136,204,0.12);color:#0088cc;">
                                <i data-lucide="bot" class="w-4 h-4"></i>
                            </div>
                            <div><div class="item-title">Bot Token</div><div class="item-subtitle">From @BotFather</div></div>
                        </div>
                        <div class="item-right" style="flex:1;max-width:220px;">
                            <input type="text" class="telegram-input" id="botTokenInput" value="" placeholder="123456:ABC-DEF..." style="max-width:220px;">
                        </div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon" style="background:rgba(0,136,204,0.12);color:#0088cc;">
                                <i data-lucide="hash" class="w-4 h-4"></i>
                            </div>
                            <div><div class="item-title">Chat ID</div><div class="item-subtitle">Your chat/group ID</div></div>
                        </div>
                        <div class="item-right" style="flex:1;max-width:220px;">
                            <input type="text" class="telegram-input" id="chatIdInput" value="" placeholder="-100123456789" style="max-width:220px;">
                        </div>
                    </div>
                    <div class="hyper-item" onclick="toggleSwitch(this)" id="autoTelegramItem">
                        <div class="item-left">
                            <div class="item-icon" style="background:rgba(0,136,204,0.12);color:#0088cc;">
                                <i data-lucide="send" class="w-4 h-4"></i>
                            </div>
                            <div><div class="item-title">Auto Send</div><div class="item-subtitle">Signal & Result to Telegram</div></div>
                        </div>
                        <div class="item-right"><div class="toggle active" id="autoTelegramToggle" data-toggle-key="autoTelegram"></div></div>
                    </div>
                </div>

                <div class="section-label">⚙️ Preferences</div>
                <div class="hyper-group">
                    <div class="hyper-item" onclick="openDialog('martingale')">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="trending-up" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Martingale</div><div class="item-subtitle">MTG Config</div></div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-martingale">No MTG</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                    <div class="hyper-item" onclick="toggleDarkMode(this)">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="moon" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Dark Mode</div><div class="item-subtitle">Theme switch</div></div>
                        </div>
                        <div class="item-right"><div class="toggle" id="darkModeToggle" data-toggle-key="darkMode"></div></div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="at-sign" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Telegram</div><div class="item-subtitle">Username for result card</div></div>
                        </div>
                        <div class="item-right">
                            <input type="text" class="telegram-input" id="telegramInput" value="@Mahabub_iX" placeholder="@username">
                        </div>
                    </div>
                    <div class="hyper-item" onclick="openDialog('navSize')">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="minimize-2" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Nav Bar Size</div><div class="item-subtitle">Bottom dock height</div></div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-navSize">Small</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                    <div class="hyper-item" onclick="openDialog('dialogAnim')">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="sparkles" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Dialog Animation</div><div class="item-subtitle">Popup effect</div></div>
                        </div>
                        <div class="item-right">
                            <span class="item-value" id="val-dialogAnim">Scale</span>
                            <i data-lucide="chevron-right" class="w-3 h-3 item-arrow"></i>
                        </div>
                    </div>
                </div>

                <div class="section-label">🎨 Appearance</div>
                <div class="hyper-group">
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="crown" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Signal Name</div><div class="item-subtitle">Signal & result format header</div></div>
                        </div>
                        <div class="item-right" style="flex:1;max-width:160px;">
                            <input type="text" class="telegram-input" id="signalNameInput" value="RAVITH AI PRO" style="max-width:160px;text-align:center;font-weight:700;">
                        </div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="type" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Dashboard Name</div><div class="item-subtitle">Shown on chart</div></div>
                        </div>
                        <div class="item-right" style="flex:1;max-width:160px;">
                            <input type="text" class="telegram-input" id="dashboardNameInput" value="RAVITH PRO" style="max-width:160px;text-align:center;font-weight:700;">
                        </div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="image" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Watermark Text</div><div class="item-subtitle">Custom chart watermark</div></div>
                        </div>
                        <div class="item-right" style="flex:1;max-width:160px;">
                            <input type="text" class="telegram-input" id="watermarkInput" value="𝐑𝐀𝐕𝐈𝐓𝐇 𝐒𝐒" style="max-width:160px;text-align:center;">
                        </div>
                    </div>
                    <div class="hyper-item" style="cursor:default;">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="eye" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Preview</div><div class="item-subtitle">Watermark preview</div></div>
                        </div>
                        <div class="item-right">
                            <span class="watermark-preview" id="watermarkPreview">𝐑𝐀𝐕𝐈𝐓𝐇 𝐒𝐒</span>
                        </div>
                    </div>
                </div>

                <div class="section-label">🎚️ Glass & Animation Controls</div>
                <div class="hyper-group">
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon" style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;"><i data-lucide="gauge" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Animation Speed</div><div class="item-subtitle">Page & indicator speed</div></div>
                        </div>
                        <div class="slider-group">
                            <span id="speedVal">1.0x</span>
                            <input type="range" min="0.4" max="2.5" step="0.1" value="1" id="speedSlider" oninput="updateAnimSpeed(this.value)">
                        </div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon" style="background:linear-gradient(135deg,#4facfe,#00f2fe);color:#fff;"><i data-lucide="droplets" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Glass Blur</div><div class="item-subtitle">Backdrop blur strength</div></div>
                        </div>
                        <div class="slider-group">
                            <span id="blurVal">32px</span>
                            <input type="range" min="8" max="50" step="1" value="32" id="blurSlider" oninput="updateGlassBlur(this.value)">
                        </div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon" style="background:linear-gradient(135deg,#a18cd1,#fbc2eb);color:#fff;"><i data-lucide="blend" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Glass Opacity</div><div class="item-subtitle">Surface transparency</div></div>
                        </div>
                        <div class="slider-group">
                            <span id="glassVal">28%</span>
                            <input type="range" min="0.10" max="0.70" step="0.05" value="0.28" id="glassSlider" oninput="updateGlassOpacity(this.value)">
                        </div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon" style="background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;"><i data-lucide="sparkles" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Indicator Glow</div><div class="item-subtitle">Nav pill shadow</div></div>
                        </div>
                        <div class="slider-group">
                            <span id="glowVal">8%</span>
                            <input type="range" min="0.02" max="0.25" step="0.02" value="0.08" id="glowSlider" oninput="updateIndicatorGlow(this.value)">
                        </div>
                    </div>
                    <div class="hyper-item">
                        <div class="item-left">
                            <div class="item-icon"><i data-lucide="type" class="w-4 h-4"></i></div>
                            <div><div class="item-title">Font Size</div><div class="item-subtitle">UI text scaling</div></div>
                        </div>
                        <div class="slider-group">
                            <span id="fontVal">12px</span>
                            <input type="range" min="11" max="18" step="1" value="12" id="fontSlider" oninput="updateFontSize(this.value)">
                        </div>
                    </div>
                </div>

                <div class="hyper-group">
                    <div class="hyper-item" onclick="resetAll()">
                        <div class="item-left">
                            <div class="item-icon" style="background:rgba(239,68,68,0.12);color:#ef4444;">
                                <i data-lucide="refresh-cw" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <div class="item-title" style="color:#ef4444;">Reset Settings</div>
                                <div class="item-subtitle">Restore defaults</div>
                            </div>
                        </div>
                        <div class="item-right"><i data-lucide="chevron-right" class="w-4 h-4 item-arrow"></i></div>
                    </div>
                </div>
            </div>

            <!-- FUTURE CHECKER VIEW -->
            <div id="view-3" class="view-container">
                <div class="fc-hero">
                    <h3>⚡ FUTURE CHECKER</h3>
                    <p>Paste signals → verify WIN / LOSS against live candles</p>
                </div>
                <div class="fc-card">
                    <div class="fc-sec">📡 Check Options</div>
                    <div class="fc-grid">
                        <div class="fc-chip" onclick="openDialog('fcDay')">
                            <span class="fc-chip-l">📅 Day</span>
                            <span class="fc-chip-v"><span id="val-fcDay">Today</span><i data-lucide="chevron-right" class="w-3 h-3"></i></span>
                        </div>
                        <div class="fc-chip" onclick="openDialog('fcMtg')">
                            <span class="fc-chip-l">🎯 MTG Level</span>
                            <span class="fc-chip-v"><span id="val-fcMtg">No MTG</span><i data-lucide="chevron-right" class="w-3 h-3"></i></span>
                        </div>
                        <div class="fc-chip" onclick="openDialog('fcPayout')">
                            <span class="fc-chip-l">💰 Min Payout</span>
                            <span class="fc-chip-v"><span id="val-fcPayout">All Payout</span><i data-lucide="chevron-right" class="w-3 h-3"></i></span>
                        </div>
                        <div class="fc-chip" onclick="fcLoadSample()">
                            <span class="fc-chip-l">📝 Sample</span>
                            <span class="fc-chip-v"><span>Insert Demo</span><i data-lucide="clipboard-paste" class="w-3 h-3"></i></span>
                        </div>
                    </div>
                </div>
                <div class="fc-card">
                    <div class="fc-sec">⚡ Paste Signals (PAIR — TIME — DIRECTION)</div>
                    <textarea id="fcSignalInput" class="fc-textarea" placeholder="Example:&#10;USDBDT OTC 14:30 CALL&#10;EURUSD OTC 14:35 PUT&#10;GBPJPY OTC 14:40 CALL"></textarea>
                    <div id="fcStatus" class="fc-status"></div>
                    <button class="fc-run-btn" id="fcCheckBtn" onclick="runFutureCheck()">🚀 CHECK SIGNALS</button>
                </div>
                <div class="fc-card" id="fcSummaryBox" style="display:none;">
                    <div class="fc-sec">📊 Summary</div>
                    <div style="display:flex;gap:6px;">
                        <div class="fc-chip-stat"><strong style="color:#22c55e;" id="fcSumWin">0</strong><span>Win</span></div>
                        <div class="fc-chip-stat"><strong style="color:#ef4444;" id="fcSumLoss">0</strong><span>Loss</span></div>
                        <div class="fc-chip-stat"><strong style="color:#f59e0b;" id="fcSumTie">0</strong><span>Tie</span></div>
                        <div class="fc-chip-stat"><strong style="color:#94a3b8;" id="fcSumPend">0</strong><span>Pend</span></div>
                        <div class="fc-chip-stat"><strong style="color:#00f2fe;" id="fcSumAcc">0%</strong><span>Acc</span></div>
                    </div>
                </div>
                <pre class="fc-result-card" id="fcResultCard"></pre>
                <div class="fc-card" id="fcCopyBox" style="display:none;text-align:center;">
                    <button class="fc-run-btn" style="margin-top:0;background:linear-gradient(135deg,#00f2fe,#4facfe);" onclick="fcCopyResult()">📋 COPY RESULT</button>
                </div>
            </div>

            <!-- PROFILE VIEW -->
            <div id="view-2" class="view-container">
                <div class="hyper-group" style="padding:24px 16px;text-align:center;">
                    <div class="profile-avatar"><i data-lucide="user" class="w-6 h-6"></i></div>
                    <h2 style="font-size:1.1rem;font-weight:700;color:var(--text);" id="profileName">User</h2>
                    <p style="font-size:0.65rem;color:var(--muted);margin-top:2px;" id="profileEmail">user@email.com</p>
                    <div class="uid-badge" id="uidBadge" onclick="copyUID()">
                        <span>UID: <strong id="profileUID">------</strong></span>
                        <span class="copy-hint" id="copyHint">Copied!</span>
                    </div>

                    <div class="profile-credit-box">
                        <div class="credit-label">Available Credits</div>
                        <div class="credit-value" id="profileCreditValue">7</div>
                        <div class="credit-type free" id="profileCreditType">FREE PLAN</div>
                        <p style="font-size:0.55rem;color:var(--muted);margin-top:8px;" id="profileCreditNote">
                            7 free signals per day. Resets daily.
                        </p>
                    </div>

                    <div class="stats-grid" style="margin-top:16px;">
                        <div class="stat-card"><span>Signals</span><strong id="profSignals">0</strong></div>
                        <div class="stat-card"><span>Win Rate</span><strong id="profRate">--%</strong></div>
                        <div class="stat-card"><span>Session</span><strong>LIVE</strong></div>
                    </div>

                    <button class="btn-logout" onclick="logoutUser()">Logout</button>
                </div>
            </div>
        </main>
    </div>

    <!-- iOS 27 LIQUID GLASS DOCK — ported from NAVIGATION.html -->
    <div class="dock-container">
        <nav class="liquid-nav glass-pill" id="liquidNav" role="tablist" aria-label="Liquid Glass Navigation" tabindex="0">
            <!-- Optical Magnifying Glass Droplet -->
            <div class="glass-droplet" id="glassDroplet" aria-hidden="true">
                <div class="lens-track" id="lensTrack">
                    <div class="lens-tab active"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M11.47 3.84a.75.75 0 011.06 0l8.69 8.69a.75.75 0 101.06-1.06l-8.689-8.69a2.25 2.25 0 00-3.182 0l-8.69 8.69a.75.75 0 001.061 1.06l8.69-8.69z" /><path d="M12 5.432l8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75V21a.75.75 0 01-.75.75H5.625a1.875 1.875 0 01-1.875-1.875v-6.198a2.29 2.29 0 00.091-.086L12 5.43z" /></svg><span>Home</span></div>
                    <div class="lens-tab"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a5.5 5.5 0 0 1 5.5 5.5c0 2.1-1.18 3.93-2.92 4.87l.35 1.63H9.07l.35-1.63A5.5 5.5 0 0 1 6.5 7.5 5.5 5.5 0 0 1 12 2zM9.5 16h5l.6 3.5a1 1 0 0 1-.98 1.17H9.88a1 1 0 0 1-.98-1.17L9.5 16z"/></svg><span>Future</span></div>
                    <div class="lens-tab"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.14 12.94a7.14 7.14 0 0 0 .05-.94 7.14 7.14 0 0 0-.05-.94l2.03-1.58a.5.5 0 0 0 .12-.63l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.03 7.03 0 0 0-1.63-.95l-.36-2.54a.5.5 0 0 0-.49-.42h-3.84a.5.5 0 0 0-.5.42l-.36 2.54c-.59.25-1.13.57-1.63.95l-2.39-.96a.5.5 0 0 0-.6.22L2.66 8.85a.5.5 0 0 0 .12.63l2.03 1.58c-.04.31-.06.62-.06.94 0 .32.02.63.06.94l-2.03 1.58a.5.5 0 0 0-.12.63l1.92 3.32c.13.22.39.31.6.22l2.39-.96c.5.38 1.04.7 1.63.95l.36 2.54c.04.25.25.42.5.42h3.84c.24 0 .46-.17.49-.42l.36-2.54c.59-.25 1.13-.57 1.63-.95l2.39.96c.21.09.47 0 .6-.22l1.92-3.32a.5.5 0 0 0-.12-.63l-2.03-1.58zM12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z"/></svg><span>Settings</span></div>
                </div>
            </div>
            <!-- Base Tabs : Home=view-0 (Engine) | Future=view-3 | Settings=view-1 -->
            <div class="nav-tab active" data-title="Home" role="tab" aria-selected="true"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M11.47 3.84a.75.75 0 011.06 0l8.69 8.69a.75.75 0 101.06-1.06l-8.689-8.69a2.25 2.25 0 00-3.182 0l-8.69 8.69a.75.75 0 001.061 1.06l8.69-8.69z" /><path d="M12 5.432l8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75V21a.75.75 0 01-.75.75H5.625a1.875 1.875 0 01-1.875-1.875v-6.198a2.29 2.29 0 00.091-.086L12 5.43z" /></svg><span>Home</span></div>
            <div class="nav-tab" data-title="Future" role="tab" aria-selected="false"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a5.5 5.5 0 0 1 5.5 5.5c0 2.1-1.18 3.93-2.92 4.87l.35 1.63H9.07l.35-1.63A5.5 5.5 0 0 1 6.5 7.5 5.5 5.5 0 0 1 12 2zM9.5 16h5l.6 3.5a1 1 0 0 1-.98 1.17H9.88a1 1 0 0 1-.98-1.17L9.5 16z"/></svg><span>Future</span></div>
            <div class="nav-tab" data-title="Settings" role="tab" aria-selected="false"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.14 12.94a7.14 7.14 0 0 0 .05-.94 7.14 7.14 0 0 0-.05-.94l2.03-1.58a.5.5 0 0 0 .12-.63l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.03 7.03 0 0 0-1.63-.95l-.36-2.54a.5.5 0 0 0-.49-.42h-3.84a.5.5 0 0 0-.5.42l-.36 2.54c-.59.25-1.13.57-1.63.95l-2.39-.96a.5.5 0 0 0-.6.22L2.66 8.85a.5.5 0 0 0 .12.63l2.03 1.58c-.04.31-.06.62-.06.94 0 .32.02.63.06.94l-2.03 1.58a.5.5 0 0 0-.12.63l1.92 3.32c.13.22.39.31.6.22l2.39-.96c.5.38 1.04.7 1.63.95l.36 2.54c.04.25.25.42.5.42h3.84c.24 0 .46-.17.49-.42l.36-2.54c.59-.25 1.13-.57 1.63-.95l2.39.96c.21.09.47 0 .6-.22l1.92-3.32a.5.5 0 0 0-.12-.63l-2.03-1.58zM12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z"/></svg><span>Settings</span></div>
        </nav>
        <!-- Separate Circular Profile Button (view-2) -->
        <button type="button" class="glass-action-btn" id="profileBtn" aria-label="Profile"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"></circle><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"></path></svg></button>
    </div>

    <script>
        /* ============================================================
           HYPERTRADE — FULL UI WITH WATERMARK & DASHBOARD ON SCREENSHOTS
           Strategies: AI Smart Signal, Support/Resistance Touch (body/wick),
           EMA Trend Cross, RSI Reversal (RSI + S/R touch)
           ============================================================ */

        // ======================== API CONFIG ========================
        const API_BASE = (function () {
            try {
                if (window.location && window.location.origin && window.location.origin !== 'null')
                    return window.location.origin;
            } catch (e) {}
            try {
                if (window.parent && window.parent.location && window.parent.location.origin)
                    return window.parent.location.origin;
            } catch (e) {}
            return '';
        })();

        // ======================== ALL MARKET PAIRS ========================
        const ALL_MARKETS = [
            'ATOUSD-OTC', 'AUDCAD-OTC', 'AUDCHF-OTC', 'AUDJPY-OTC', 'AUDNZD-OTC',
            'AUDUSD-OTC', 'AVAUSD-OTC', 'AXSUSD-OTC', 'BCHUSD-OTC', 'BNBUSD-OTC',
            'BRLUSD-OTC', 'BTCUSD-OTC', 'CADCHF-OTC', 'CADJPY-OTC', 'CHFJPY-OTC',
            'DASUSD-OTC', 'DOTUSD-OTC', 'ETCUSD-OTC', 'ETHUSD-OTC', 'EURAUD-OTC',
            'EURCAD-OTC', 'EURCHF-OTC', 'EURGBP-OTC', 'EURJPY-OTC', 'EURNZD-OTC',
            'EURUSD-OTC', 'GBPAUD-OTC', 'GBPCAD-OTC', 'GBPCHF-OTC', 'GBPJPY-OTC',
            'GBPNZD-OTC', 'GBPUSD-OTC', 'LINUSD-OTC', 'LTCUSD-OTC', 'NZDCAD-OTC',
            'NZDCHF-OTC', 'NZDJPY-OTC', 'NZDUSD-OTC', 'SOLUSD-OTC', 'TONUSD-OTC',
            'TRUUSD-OTC', 'UKBrent-OTC', 'USCrude-OTC', 'USDARS-OTC', 'USDBDT-OTC',
            'USDCAD-OTC', 'USDCHF-OTC', 'USDCOP-OTC', 'USDDZD-OTC', 'USDEGP-OTC',
            'USDIDR-OTC', 'USDINR-OTC', 'USDJPY-OTC', 'USDMXN-OTC', 'USDNGN-OTC',
            'USDPHP-OTC', 'USDPKR-OTC', 'USDZAR-OTC', 'XAGUSD-OTC', 'XAUUSD-OTC',
            'XRPUSD-OTC', 'ZECUSD-OTC'
        ];

        let selectedAutoMarkets = [...ALL_MARKETS];

        // ======================== AUTH SYSTEM ========================
        let currentUser = null;
        let settingsLoaded = false;

        function showToast(msg, duration = 2000) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), duration);
        }

        function loadSession() {
            const saved = localStorage.getItem('hypertrade_session');
            if (saved) { try { currentUser = JSON.parse(saved); return true; } catch { return false; } }
            return false;
        }

        function saveSession(userData) {
            currentUser = userData;
            localStorage.setItem('hypertrade_session', JSON.stringify(userData));
        }

        function clearSession() {
            localStorage.removeItem('hypertrade_session');
            Object.keys(localStorage).forEach(k => {
                if (k.startsWith('hypertrade_settings_')) localStorage.removeItem(k);
            });
            currentUser = null;
        }

        function isLoggedIn() { return currentUser !== null; }

        function setAuthVisibility(visible) { document.getElementById('authOverlay').classList.toggle('visible', visible); }

        // ======================== PASSWORD GATE (SERVER-SIDE VALIDATED) ========================
        async function handleLogin() {
            const password = document.getElementById('gatePassword').value;
            const errorEl = document.getElementById('loginError');
            if (!password) { errorEl.innerText = 'Please enter the password.'; return; }
            errorEl.innerText = 'Checking...';
            try {
                const res = await fetch(API_BASE + '/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password })
                });
                const data = await res.json();
                if (data.success) {
                    errorEl.innerText = '';
                    document.getElementById('gatePassword').value = '';
                    saveSession({
                        email: data.email,
                        name: data.name,
                        uid: data.uid,
                        credit: data.credit,
                        credit_type: data.credit_type,
                        settings: data.settings || null
                    });
                    setAuthVisibility(false);
                    initEngine();
                } else { errorEl.innerText = data.message || 'Wrong password.'; }
            } catch (err) { errorEl.innerText = 'Server error. Make sure Flask is running.'; console.error(err); }
        }
        document.getElementById('gateForm').addEventListener('submit', function (e) { e.preventDefault(); handleLogin(); });
        document.getElementById('gatePassword').addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); handleLogin(); }
        });

        function logoutUser() {
            try { flushSettingsNow(); } catch (e) {}
            try { stopResultPolling();
                stopAutoMode();
                stopLiveTicks(); } catch (e) {}
            settingsLoaded = false;
            clearSession();
            setAuthVisibility(true);
            setTimeout(() => location.reload(), 200);
        }

        function copyUID() {
            if (!currentUser || !currentUser.uid) return;
            const uid = currentUser.uid;
            if (navigator.clipboard) {
                navigator.clipboard.writeText(uid).then(() => {
                    const badge = document.getElementById('uidBadge');
                    badge.classList.add('copied');
                    showToast('UID copied: ' + uid);
                    setTimeout(() => badge.classList.remove('copied'), 2000);
                });
            } else {
                const ta = document.createElement('textarea');
                ta.value = uid;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast('UID copied: ' + uid);
            }
        }

        function updateProfileUI() {
            if (!currentUser) return;
            document.getElementById('profileName').innerText = currentUser.name || 'User';
            document.getElementById('profileEmail').innerText = currentUser.email || '';
            document.getElementById('profileUID').innerText = currentUser.uid || '------';
            const creditVal = document.getElementById('profileCreditValue');
            const creditType = document.getElementById('profileCreditType');
            const creditNote = document.getElementById('profileCreditNote');
            const headerBadge = document.getElementById('headerCreditBadge');
            if (currentUser.credit_type === 'pro') {
                creditVal.innerText = '∞';
                creditType.className = 'credit-type pro';
                creditType.innerText = 'PRO PLAN';
                creditNote.innerText = 'Unlimited signals. Pro subscription active.';
                headerBadge.className = 'credit-badge pro';
                headerBadge.innerText = '⚡ PRO';
            } else {
                const c = typeof currentUser.credit === 'number' ? currentUser.credit : 7;
                creditVal.innerText = c;
                creditType.className = 'credit-type free';
                creditType.innerText = 'FREE PLAN';
                creditNote.innerText = `${c} signal${c !== 1 ? 's' : ''} remaining today. Resets daily.`;
                headerBadge.className = 'credit-badge';
                headerBadge.innerText = '⚡ ' + c;
            }
        }

        async function fetchUserCount() {
            try {
                const res = await fetch(API_BASE + '/total-users', { cache: 'no-store' });
                const data = await res.json();
                if (data.success) {
                    const n = (data.count !== undefined ? data.count : data.total) || 0;
                    const el = document.getElementById('userCountText');
                    if (el) el.innerText = String(n);
                }
            } catch (e) {
                const el = document.getElementById('userCountText');
                if (el && (!el.innerText || el.innerText === '0')) el.innerText = '—';
            }
        }

        async function refreshProfile() {
            if (!currentUser || !currentUser.email) return;
            try {
                const res = await fetch(API_BASE + '/profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: currentUser.email })
                });
                const data = await res.json();
                if (data.success) {
                    currentUser.name = data.name;
                    currentUser.uid = data.uid;
                    currentUser.credit = data.credit;
                    currentUser.credit_type = data.credit_type;
                    saveSession(currentUser);
                    updateProfileUI();
                }
            } catch (e) { console.warn('Profile refresh failed'); }
        }

        async function useOneCredit() {
            if (!currentUser) return false;
            if (currentUser.credit_type === 'pro') return true;
            try {
                const res = await fetch(API_BASE + '/use-credit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: currentUser.email })
                });
                const data = await res.json();
                if (data.success) {
                    if (data.credit_type === 'pro') { currentUser.credit_type = 'pro';
                        currentUser.credit = 'unlimited'; } else { currentUser.credit = data.credit;
                        currentUser.credit_type = data.credit_type || 'free'; }
                    saveSession(currentUser);
                    updateProfileUI();
                    return true;
                } else { showToast(data.message || 'No credits remaining!'); return false; }
            } catch (e) { console.warn('Credit use failed'); return false; }
        }

        function hasCredits() {
            if (!currentUser) return false;
            if (currentUser.credit_type === 'pro') return true;
            return (typeof currentUser.credit === 'number' && currentUser.credit > 0);
        }

        // ======================== PERSISTENT SETTINGS ========================
        function getSettingsKey() {
            if (!currentUser) return 'hypertrade_settings_default';
            return `hypertrade_settings_${currentUser.email}`;
        }

        function collectSettings() {
            return {
                market: document.getElementById('val-market').innerText,
                timeframe: document.getElementById('val-timeframe').innerText,
                strategy: document.getElementById('val-strategy').innerText,
                chartType: document.getElementById('val-chartType').innerText,
                chartStyle: (document.getElementById('val-chartStyle') || {innerText:'Style 1 - Classic'}).innerText,
                martingale: document.getElementById('val-martingale').innerText,
                dialogAnim: document.getElementById('val-dialogAnim').innerText,
                signalMode: document.getElementById('val-signalMode').innerText,
                telegram: document.getElementById('telegramInput').value,
                botToken: document.getElementById('botTokenInput').value,
                chatId: document.getElementById('chatIdInput').value,
                darkMode: document.getElementById('darkModeToggle').classList.contains('active'),
                autoTelegram: document.getElementById('autoTelegramToggle').classList.contains('active'),
                soundAlerts: !!(document.querySelector('[data-toggle-key="soundAlerts"]') || {}).classList?.contains(
                    'active'),
                vibration: !!(document.querySelector('[data-toggle-key="vibration"]') || {}).classList?.contains(
                    'active'),
                speed: document.getElementById('speedSlider').value,
                glass: document.getElementById('glassSlider').value,
                fontSize: document.getElementById('fontSlider').value,
                navSize: (document.getElementById('val-navSize') || { innerText: 'Small' }).innerText,
                dashboardName: document.getElementById('dashboardNameInput').value,
                watermarkText: document.getElementById('watermarkInput').value,
                signalName: document.getElementById('signalNameInput').value,
                autoMarkets: selectedAutoMarkets,
                stats: engine.stats,
                tradeHistory: tradeHistory
            };
        }

        let _saveTimer = null;

        function saveSettings() {
            if (!settingsLoaded) return;
            const settings = collectSettings();
            const key = getSettingsKey();
            try { localStorage.setItem(key, JSON.stringify(settings)); } catch (e) {}
            if (!currentUser || !currentUser.email) return;
            if (_saveTimer) clearTimeout(_saveTimer);
            _saveTimer = setTimeout(() => { pushSettingsToServer(settings); }, 800);
        }

        function flushSettingsNow() {
            if (!settingsLoaded) return;
            const settings = collectSettings();
            try { localStorage.setItem(getSettingsKey(), JSON.stringify(settings)); } catch (e) {}
            if (!currentUser || !currentUser.email) return;
            try {
                const body = JSON.stringify({ email: currentUser.email, settings });
                if (navigator.sendBeacon) {
                    const blob = new Blob([body], { type: 'application/json' });
                    navigator.sendBeacon(API_BASE + '/save-settings', blob);
                } else {
                    fetch(API_BASE + '/save-settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body,
                        keepalive: true
                    });
                }
            } catch (e) { /* ignore */ }
        }

        async function pushSettingsToServer(settings) {
            if (!currentUser || !currentUser.email) return;
            try {
                await fetch(API_BASE + '/save-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: currentUser.email, settings })
                });
            } catch (e) { console.warn('server save failed'); }
        }

        function applySettings(s) {
            if (!s) return;
            if (s.market) document.getElementById('val-market').innerText = s.market;
            if (s.timeframe) document.getElementById('val-timeframe').innerText = s.timeframe;
            if (s.strategy) document.getElementById('val-strategy').innerText = s.strategy;
            if (s.chartType) document.getElementById('val-chartType').innerText = s.chartType;
            if (s.chartStyle && document.getElementById('val-chartStyle')) document.getElementById('val-chartStyle').innerText = s.chartStyle;
            if (s.martingale) document.getElementById('val-martingale').innerText = s.martingale;
            if (s.dialogAnim) { document.getElementById('val-dialogAnim').innerText = s.dialogAnim;
                dialogAnimStyle = s.dialogAnim; }
            if (s.signalMode) { document.getElementById('val-signalMode').innerText = s.signalMode;
                onSignalModeChanged(s.signalMode, true); }
            if (typeof s.telegram === 'string') document.getElementById('telegramInput').value = s.telegram;
            if (typeof s.botToken === 'string') document.getElementById('botTokenInput').value = s.botToken;
            if (typeof s.chatId === 'string') document.getElementById('chatIdInput').value = s.chatId;
            if (s.darkMode) { document.getElementById('darkModeToggle').classList.add('active');
                document.body.classList.add('dark-mode'); } else { document.getElementById('darkModeToggle').classList
                    .remove('active');
                document.body.classList.remove('dark-mode'); }
            if (s.autoTelegram) document.getElementById('autoTelegramToggle').classList.add('active');
            else document.getElementById('autoTelegramToggle').classList.remove('active');

            const soundToggle = document.querySelector('[data-toggle-key="soundAlerts"]');
            const vibToggle = document.querySelector('[data-toggle-key="vibration"]');
            if (soundToggle) soundToggle.classList.toggle('active', s.soundAlerts !== false);
            if (vibToggle) vibToggle.classList.toggle('active', s.vibration !== false);

            if (s.speed) { document.getElementById('speedSlider').value = s.speed;
                document.documentElement.style.setProperty('--speed-multiplier', parseFloat(s.speed));
                document.getElementById('speedVal').innerText = parseFloat(s.speed).toFixed(1) + 'x'; }
            if (s.glass) { document.getElementById('glassSlider').value = s.glass;
                document.documentElement.style.setProperty('--glass-alpha', parseFloat(s.glass));
                document.getElementById('glassVal').innerText = Math.round(parseFloat(s.glass) * 100) + '%'; }
            if (s.fontSize) { document.getElementById('fontSlider').value = s.fontSize;
                document.documentElement.style.fontSize = s.fontSize + 'px';
                document.getElementById('fontVal').innerText = s.fontSize + 'px'; }
            if (s.navSize) { const nsEl = document.getElementById('val-navSize');
                if (nsEl) nsEl.innerText = s.navSize;
                applyNavSize(s.navSize, true); }
            if (s.dashboardName) { document.getElementById('dashboardNameInput').value = s.dashboardName;
                document.documentElement.style.setProperty('--dashboard-name', '"' + s.dashboardName + '"'); }
            if (s.watermarkText) { document.getElementById('watermarkInput').value = s.watermarkText;
                document.getElementById('watermarkPreview').innerText = s.watermarkText;
                document.documentElement.style.setProperty('--watermark-text', '"' + s.watermarkText + '"'); }
            if (s.signalName) document.getElementById('signalNameInput').value = s.signalName;
            if (Array.isArray(s.autoMarkets) && s.autoMarkets.length) selectedAutoMarkets = s.autoMarkets.slice();
            if (s.stats && typeof s.stats === 'object') {
                engine.stats.wins = Number(s.stats.wins) || 0;
                engine.stats.losses = Number(s.stats.losses) || 0;
                engine.stats.streakW = Number(s.stats.streakW) || 0;
                engine.stats.streakL = Number(s.stats.streakL) || 0;
            }
            if (Array.isArray(s.tradeHistory)) tradeHistory = s.tradeHistory.slice();

            updateStatsUI();
            const count = selectedAutoMarkets.length;
            document.getElementById('val-autoMarkets').innerText = count === ALL_MARKETS.length ? 'All' : count + ' pairs';
        }

        async function loadSettings() {
            let applied = false;
            if (currentUser && currentUser.settings) {
                applySettings(currentUser.settings);
                applied = true;
            }
            if (currentUser && currentUser.email) {
                try {
                    const res = await fetch(API_BASE + '/get-settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: currentUser.email })
                    });
                    const data = await res.json();
                    if (data && data.success && data.settings) {
                        applySettings(data.settings);
                        applied = true;
                        try { localStorage.setItem(getSettingsKey(), JSON.stringify(data.settings)); } catch (e) {}
                    }
                } catch (e) { /* offline fallback below */ }
            }
            if (!applied) {
                const raw = localStorage.getItem(getSettingsKey());
                if (raw) { try { applySettings(JSON.parse(raw)); } catch (e) {} }
            }
            settingsLoaded = true;
        }

        // ============ VIEW SWITCHING + iOS 27 LIQUID GLASS NAV (from NAVIGATION.html) ============
        let currentView = 0;
        // tab slot -> view id : slot0=Home(view-0) | slot1=Future(view-3) | slot2=Settings(view-1) | Profile(view-2) via separate button
        const navOrder = [0, 3, 1, 2];
        let liquidNavAPI = null;

        function switchView(index) {
            const same = index === currentView;
            if (!same) {
                const oldViewEl = document.getElementById('view-' + currentView);
                const newViewEl = document.getElementById('view-' + index);
                if (!newViewEl) return;
                const slideLeft = index > currentView;
                if (oldViewEl) {
                    oldViewEl.className = 'view-container active';
                    void oldViewEl.offsetWidth;
                    oldViewEl.classList.add(slideLeft ? 'exit-left' : 'exit-right');
                    oldViewEl.classList.remove('active');
                }
                newViewEl.className = 'view-container';
                newViewEl.style.transform = slideLeft ? 'translateX(36px)' : 'translateX(-36px)';
                newViewEl.style.opacity = '0';
                void newViewEl.offsetWidth;
                newViewEl.classList.add('active');
                newViewEl.style.transform = '';
                newViewEl.style.opacity = '';
                currentView = index;
            }
            if (liquidNavAPI) liquidNavAPI.sync(index);
            if (!same) {
                if (index === 0) setTimeout(chartResize, 50);
                if (index === 2) refreshProfile();
                try { if (window.lucide) lucide.createIcons(); } catch(e){}
            }
        }

        function setupLiquidNav() {
            const navEl = document.getElementById('liquidNav');
            const dropletEl = document.getElementById('glassDroplet');
            const lensTrackEl = document.getElementById('lensTrack');
            const profileBtn = document.getElementById('profileBtn');
            if (!navEl || !dropletEl || !lensTrackEl || navEl.dataset.liquidBound) return;
            navEl.dataset.liquidBound = '1';

            const baseTabs = Array.prototype.slice.call(navEl.querySelectorAll('.nav-tab'));
            const lensTabs = Array.prototype.slice.call(lensTrackEl.querySelectorAll('.lens-tab'));
            const TAB_COUNT = baseTabs.length;
            const INSET = 5;

            let trackWidth = 0, tabWidth = 0;
            let selectedIndex = Math.max(0, navOrder.indexOf(currentView));

            let posX = 0, targetX = 0, velX = 0;
            let scale = 1, targetScale = 1, scaleVel = 0;

            let pointerDown = false, dragging = false, pointerId = null;
            let startX = 0, grabOffset = 0, settleTimer = null;

            function clamp(v, min, max) { return v < min ? min : (v > max ? max : v); }

            function updateLayout() {
                const rect = navEl.getBoundingClientRect();
                if (rect.width < 20) return;
                trackWidth = rect.width - INSET * 2;
                tabWidth = trackWidth / TAB_COUNT;
                dropletEl.style.width = tabWidth + 'px';
                lensTrackEl.style.width = trackWidth + 'px';
                targetX = selectedIndex * tabWidth;
                if (!pointerDown) { posX = targetX; velX = 0; }
                render();
            }

            function syncActiveTab(slot) {
                slot = clamp(slot, 0, TAB_COUNT - 1);
                selectedIndex = slot;
                baseTabs.forEach(function (tab, i) {
                    const on = (i === slot);
                    tab.classList.toggle('active', on);
                    tab.setAttribute('aria-selected', String(on));
                });
                lensTabs.forEach(function (tab, i) {
                    tab.classList.toggle('active', i === slot);
                });
            }

            function render() {
                const speed = Math.abs(velX);
                const sx = scale + Math.min(speed * 0.0055, 0.14);
                const sy = scale - Math.min(speed * 0.0022, 0.05);
                dropletEl.style.transform = 'translate3d(' + posX + 'px, 0, 0) scale(' + sx + ', ' + sy + ')';
                lensTrackEl.style.transform = 'translate3d(' + (-posX) + 'px, 0, 0)';
                const magnified = pointerDown || scale > 1.03 || speed > 0.35;
                dropletEl.classList.toggle('is-magnified', magnified);
                navEl.classList.toggle('is-interacting', magnified);
                baseTabs.forEach(function (tab, idx) {
                    const under = magnified && Math.abs(posX - idx * tabWidth) < tabWidth * 0.6;
                    tab.classList.toggle('under-lens', under);
                });
                if (magnified && tabWidth > 0) {
                    const hoverIndex = clamp(Math.round(posX / tabWidth), 0, TAB_COUNT - 1);
                    if (hoverIndex !== selectedIndex) syncActiveTab(hoverIndex);
                }
            }

            function localXFromEvent(e) {
                const rect = navEl.getBoundingClientRect();
                return e.clientX - rect.left - INSET;
            }

            function onPointerDown(e) {
                if (pointerDown || tabWidth <= 0) return;
                if (e.pointerType === 'mouse' && e.button !== 0) return;
                clearTimeout(settleTimer);
                pointerDown = true; dragging = false;
                pointerId = e.pointerId; startX = e.clientX;
                try { navEl.setPointerCapture(e.pointerId); } catch (err) {}
                const localX = localXFromEvent(e);
                const hitIndex = clamp(Math.floor(localX / tabWidth), 0, TAB_COUNT - 1);
                targetScale = 1.16;
                if (localX >= posX - 8 && localX <= posX + tabWidth + 8) {
                    grabOffset = localX - posX;
                } else {
                    grabOffset = tabWidth * 0.5;
                    targetX = hitIndex * tabWidth;
                    syncActiveTab(hitIndex);
                }
            }

            function onPointerMove(e) {
                if (!pointerDown) return;
                if (pointerId !== null && e.pointerId !== pointerId) return;
                if (Math.abs(e.clientX - startX) > 4) dragging = true;
                if (!dragging) return;
                const localX = localXFromEvent(e);
                const maxX = trackWidth - tabWidth;
                let nextX = localX - grabOffset;
                if (nextX < 0) { nextX *= 0.25; }
                else if (nextX > maxX) { nextX = maxX + (nextX - maxX) * 0.25; }
                targetX = nextX;
                targetScale = 1.22;
            }

            function commitSlot(slot) {
                slot = clamp(slot, 0, TAB_COUNT - 1);
                targetX = slot * tabWidth;
                targetScale = 1;
                syncActiveTab(slot);
                if (navOrder[slot] !== currentView) switchView(navOrder[slot]);
                else if (liquidNavAPI) liquidNavAPI.sync(currentView);
            }

            function onPointerUp(e) {
                if (!pointerDown) return;
                const isCancel = e && e.type === 'pointercancel';
                const wasDragging = dragging;
                let localX = 0;
                if (!isCancel && e && typeof e.clientX === 'number') localX = localXFromEvent(e);
                pointerDown = false; pointerId = null; dragging = false;
                if (isCancel) {
                    commitSlot(clamp(Math.round(targetX / tabWidth), 0, TAB_COUNT - 1));
                    return;
                }
                if (wasDragging) {
                    commitSlot(clamp(Math.round(targetX / tabWidth), 0, TAB_COUNT - 1));
                    if (navigator.vibrate) try { navigator.vibrate(8); } catch (err) {}
                } else {
                    const tapped = clamp(Math.floor(localX / tabWidth), 0, TAB_COUNT - 1);
                    targetX = tapped * tabWidth;
                    targetScale = 1.16;
                    syncActiveTab(tapped);
                    if (navOrder[tapped] !== currentView) switchView(navOrder[tapped]);
                    settleTimer = setTimeout(function () { if (!pointerDown) targetScale = 1; }, 220);
                }
            }

            navEl.addEventListener('pointerdown', onPointerDown);
            window.addEventListener('pointermove', onPointerMove, { passive: true });
            window.addEventListener('pointerup', onPointerUp);
            window.addEventListener('pointercancel', onPointerUp);

            navEl.addEventListener('keydown', function (e) {
                let next = selectedIndex;
                if (e.key === 'ArrowRight') next = selectedIndex + 1;
                else if (e.key === 'ArrowLeft') next = selectedIndex - 1;
                else if (e.key === 'Home') next = 0;
                else if (e.key === 'End') next = TAB_COUNT - 1;
                else return;
                e.preventDefault();
                clearTimeout(settleTimer);
                targetX = clamp(next, 0, TAB_COUNT - 1) * tabWidth;
                targetScale = 1.16;
                syncActiveTab(clamp(next, 0, TAB_COUNT - 1));
                if (navOrder[clamp(next, 0, TAB_COUNT - 1)] !== currentView) switchView(navOrder[clamp(next, 0, TAB_COUNT - 1)]);
                settleTimer = setTimeout(function () { if (!pointerDown) targetScale = 1; }, 220);
            });

            if (profileBtn) profileBtn.addEventListener('click', function () { switchView(2); });

            function step() {
                if (!document.hidden && tabWidth > 0) {
                    const stiffness = dragging ? 0.42 : 0.18;
                    const damping = 0.72;
                    velX = (velX + (targetX - posX) * stiffness) * damping;
                    posX += velX;
                    scaleVel = (scaleVel + (targetScale - scale) * 0.22) * 0.68;
                    scale += scaleVel;
                    render();
                }
                requestAnimationFrame(step);
            }

            if (window.ResizeObserver) {
                const ro = new ResizeObserver(function () { updateLayout(); });
                ro.observe(navEl);
            }
            window.addEventListener('resize', updateLayout);
            window.addEventListener('orientationchange', function () { setTimeout(updateLayout, 150); });
            window.addEventListener('load', updateLayout);

            updateLayout();
            requestAnimationFrame(step);

            liquidNavAPI = {
                sync: function (viewIndex) {
                    if (viewIndex === 2) {
                        if (profileBtn) {
                            profileBtn.classList.add('is-active');
                            setTimeout(function () { profileBtn.classList.remove('is-active'); }, 1200);
                        }
                        return;
                    }
                    const slot = navOrder.indexOf(viewIndex);
                    if (slot < 0) return;
                    clearTimeout(settleTimer);
                    targetX = slot * tabWidth;
                    if (!pointerDown) { syncActiveTab(slot); }
                    if (!pointerDown) { posX = targetX; velX = 0; render(); }
                }
            };
            liquidNavAPI.sync(currentView);
        }

        // init after DOM ready (also initializes iOS-style range fill)
        function initLiquidUI() {
            setupLiquidNav();
            document.querySelectorAll('input[type="range"]').forEach(updateRangeFill);
            setTimeout(function () {
                document.querySelectorAll('input[type="range"]').forEach(updateRangeFill);
            }, 600);
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initLiquidUI);
        } else {
            setTimeout(initLiquidUI, 50);
        }

        // ======================== OPTIONS & DIALOG ========================
        const optionsData = {
            market: { title: 'Select Market Pair', items: ALL_MARKETS },
            timeframe: { title: 'Select Timeframe', items: ['30 Seconds', '1 Minute', '2 Minutes', '5 Minutes',
                    '15 Minutes'
                ] },
            strategy: { title: 'Select Strategy', items: [
                    'AI Smart Signal', 'Support/Resistance Touch', 'EMA Trend Cross', 'RSI Reversal',
                    'Bollinger Bands', 'MACD Momentum', 'Stochastic Reversal', 'Trend Pullback', 'Breakout Spike'
                ] },
            chartType: { title: 'Select Chart Type', items: ['Candlestick', 'Line', 'Area', 'Heikin Ashi'] },
            chartStyle: { title: 'Chart Style (26 Designs)', items: [
                    'Style 1 - Classic', 'Style 2 - Terminal', 'Style 3 - Futuristic', 'Style 4 - Pro Finance',
                    'Style 5 - Neon Pulse', 'Style 6 - Deep Ocean', 'Style 7 - Sunset Drive', 'Style 8 - Royal Violet',
                    'Style 9 - Cyber Grid', 'Style 10 - Galaxy Starfield', 'Style 11 - Matrix Rain', 'Style 12 - Aurora Borealis',
                    'Style 13 - Golden Bull', 'Style 14 - Ice Crystal', 'Style 15 - Retro Wave', 'Style 16 - Holo 3D Depth',
                    'Style 17 - Quantum Flux', 'Style 18 - Stealth Ops', 'Style 19 - Plasma Storm', 'Style 20 - Limon Kombiner Pro',
                    'Style 21 - Aurora Quantum', 'Style 22 - Cyber Matrix', 'Style 23 - Orbital Glass', 'Style 24 - Dark Phoenix',
                    'Style 25 - Nexus Ultra', 'Style 26 - Quantum Glass Infinity'
                ] },
            martingale: { title: 'Martingale Steps', items: ['No MTG', 'MTG1', 'MTG2', 'MTG3'] },
            dialogAnim: { title: 'Dialog Animation', items: ['Scale', 'Fade', 'Slide Up', 'Flip', 'Bounce'] },
            signalMode: { title: 'Signal Mode', items: ['Manual', 'Auto'] },
            navSize: { title: 'Nav Bar Size', items: ['Small', 'Normal'] },
            fcDay: { title: 'Select Day', items: ['Today', 'Yesterday'] },
            fcMtg: { title: 'MTG Level', items: ['No MTG', 'MTG1', 'MTG2', 'MTG3'] },
            fcPayout: { title: 'Min Payout Filter', items: ['All Payout', '80%+', '85%+', '90%+', '92%+'] }
        };

        let activeDialogType = '';
        let dialogAnimStyle = 'Scale';

        function openDialog(type) {
            if (type === 'autoMarkets') { openAutoMarketsDialog(); return; }
            activeDialogType = type;
            const data = optionsData[type];
            const currentValue = document.getElementById(`val-${type}`).innerText;
            document.getElementById('dialogTitle').innerText = data.title;
            const listHtml = data.items.map(item => {
                const isSelected = item === currentValue;
                return `<div class="dialog-item ${isSelected ? 'selected' : ''}" onclick="selectItem('${item}', event)">
                    <span>${item}</span>
                    <i data-lucide="check" class="w-4 h-4 check-icon"></i>
                </div>`;
            }).join('');
            document.getElementById('dialogList').innerHTML = listHtml;
            lucide.createIcons();
            showDialogAnim();
        }

        function openAutoMarketsDialog() {
            activeDialogType = 'autoMarkets';
            document.getElementById('dialogTitle').innerText = 'Select Auto Markets';
            const listHtml = ALL_MARKETS.map(item => {
                const checked = selectedAutoMarkets.includes(item);
                return `<div class="dialog-item" onclick="toggleAutoMarket('${item}', this)">
                    <span>${item}</span>
                    <div class="check-box ${checked ? 'checked' : ''}"></div>
                </div>`;
            }).join('') +
                `<div class="dialog-item" style="justify-content:center;margin-top:6px;">
                <button onclick="closeDialog()" style="padding:8px 24px;border-radius:10px;background:var(--primary);color:white;border:none;font-weight:600;font-size:0.7rem;cursor:pointer;">DONE</button>
            </div>`;
            document.getElementById('dialogList').innerHTML = listHtml;
            showDialogAnim();
        }

        function toggleAutoMarket(market, el) {
            const box = el.querySelector('.check-box');
            const idx = selectedAutoMarkets.indexOf(market);
            if (idx >= 0) { selectedAutoMarkets.splice(idx, 1);
                box.classList.remove('checked'); } else { selectedAutoMarkets.push(market);
                box.classList.add('checked'); }
            const count = selectedAutoMarkets.length;
            document.getElementById('val-autoMarkets').innerText = count === ALL_MARKETS.length ? 'All' : count + ' pairs';
            saveSettings();
        }

        function showDialogAnim() {
            const dialog = document.getElementById('selectionDialog');
            dialog.classList.remove('anim-scale', 'anim-fade', 'anim-slide-up', 'anim-flip', 'anim-bounce');
            switch (dialogAnimStyle) {
                case 'Fade':
                    dialog.classList.add('anim-fade');
                    break;
                case 'Slide Up':
                    dialog.classList.add('anim-slide-up');
                    break;
                case 'Flip':
                    dialog.classList.add('anim-flip');
                    break;
                case 'Bounce':
                    dialog.classList.add('anim-bounce');
                    break;
                default:
                    dialog.classList.add('anim-scale');
            }
            document.getElementById('overlay').classList.add('show');
            dialog.classList.add('show');
            document.getElementById('app-wrapper').classList.add('blur-active');
        }

        function closeDialog() {
            document.getElementById('overlay').classList.remove('show');
            document.getElementById('selectionDialog').classList.remove('show');
            document.getElementById('app-wrapper').classList.remove('blur-active');
        }

        // ============ DRAGGABLE ZOOM INDICATOR ON SELECTION DIALOG (nav-bar style) ============
        // Drag anywhere on the dialog list: a glass droplet indicator follows the
        // finger, magnifies/zooms the item under it (like the nav bar), and on
        // release selects that item with a spring bounce.
        function setupDialogDroplet() {
            const dialog = document.getElementById('selectionDialog');
            const list = document.getElementById('dialogList');
            if (!dialog || !list || dialog.dataset.dropletBound) return;
            dialog.dataset.dropletBound = '1';

            const droplet = document.createElement('div');
            droplet.className = 'dialog-droplet';
            dialog.querySelector('.dialog-title').insertAdjacentElement('afterend', droplet);

            let active = false, itemH = 0, startY = 0;
            let curY = 0, curScale = 1, tgtY = 0, tgtScale = 1, velY = 0, rafId = null;
            let touchId = null;

            function itemCount() { return list.querySelectorAll('.dialog-item').length; }

            function dropletY(itemIdx) {
                const it = list.querySelectorAll('.dialog-item')[itemIdx];
                if (!it) return 0;
                return it.offsetTop + it.offsetHeight / 2 - list.offsetTop;
            }

            function render() {
                droplet.style.transform = 'translateY(' + (curY - droplet.offsetHeight / 2) + 'px) scale(1, ' + curScale + ')';
                droplet.style.opacity = '1';
            }

            function highlightAt(y) {
                const items = list.querySelectorAll('.dialog-item');
                let best = -1, bestD = Infinity;
                items.forEach(function (it, i) {
                    const c = it.offsetTop + it.offsetHeight / 2 - list.offsetTop;
                    const d = Math.abs(c - y);
                    if (d < bestD) { bestD = d; best = i; }
                });
                items.forEach(function (it, i) {
                    const near = (i === best && bestD < itemH * 0.9);
                    it.style.transform = near ? 'scale(' + (1 + 0.08 * (1 - bestD / (itemH * 0.9))) + ')' : '';
                });
                return best;
            }

            function step() {
                if (active || Math.abs(tgtY - curY) > 0.5 || Math.abs(tgtScale - curScale) > 0.005) {
                    const stiff = active ? 0.4 : 0.16;
                    velY = (velY + (tgtY - curY) * stiff) * 0.7;
                    curY += velY;
                    curScale += (tgtScale - curScale) * (active ? 0.3 : 0.16);
                    render();
                    if (active) highlightAt(curY);
                } else if (!active && droplet.style.opacity === '1') {
                    droplet.style.opacity = '0';
                    list.querySelectorAll('.dialog-item').forEach(function (it) { it.style.transform = ''; });
                }
                rafId = requestAnimationFrame(step);
            }
            rafId = requestAnimationFrame(step);

            function localY(e) {
                const r = list.getBoundingClientRect();
                const dr = dialog.getBoundingClientRect();
                return e.clientY - r.top + (dr.top - dialog.getBoundingClientRect().top) * 0 + (r.top - dr.top);
            }

            function posInList(e) {
                // position relative to list (handles internal scrolling)
                const r = list.getBoundingClientRect();
                return e.clientY - r.top + list.scrollTop;
            }

            dialog.addEventListener('pointerdown', function (e) {
                if (!dialog.classList.contains('show')) return;
                if (e.target.closest('.dialog-item') && e.target.closest('button')) return;
                if (e.target.closest('.dialog-item')) return; // taps handled by items
                if (!e.target.closest('.dialog-list') && e.target !== list) return;
                active = true; touchId = e.pointerId;
                e.preventDefault();
                const items = list.querySelectorAll('.dialog-item');
                if (!items.length) return;
                itemH = items[0].offsetHeight;
                startY = posInList(e);
                curY = tgtY = startY; curScale = tgtScale = 1.15; velY = 0;
                droplet.classList.add('is-zoomed');
                render();
                try { dialog.setPointerCapture(e.pointerId); } catch (err) {}
            });

            dialog.addEventListener('pointermove', function (e) {
                if (!active || e.pointerId !== touchId) return;
                const y = posInList(e);
                const count = itemCount();
                const maxY = count ? dropletY(count - 1) : y;
                let ny = y;
                if (ny < 0) ny *= 0.3;
                else if (ny > maxY) ny = maxY + (ny - maxY) * 0.3;
                tgtY = ny;
                tgtScale = 1.22;
            });

            function finish(e) {
                if (!active || (e && e.pointerId !== touchId && e.type !== 'pointercancel')) return;
                active = false; touchId = null;
                droplet.classList.remove('is-zoomed');
                const idx = highlightAt(curY);
                const items = list.querySelectorAll('.dialog-item');
                tgtScale = 1;
                if (idx >= 0 && items[idx] && !items[idx].querySelector('button')) {
                    // spring-snap droplet onto the chosen item, then select it
                    tgtY = dropletY(idx);
                    items[idx].classList.add('selected');
                    setTimeout(function () {
                        const ev = new Event('bypass', { bubbles: false });
                        try { items[idx].click(); } catch (err) {}
                    }, 160);
                }
                setTimeout(function () {
                    list.querySelectorAll('.dialog-item').forEach(function (it) { it.style.transform = ''; });
                }, 260);
            }
            dialog.addEventListener('pointerup', finish);
            dialog.addEventListener('pointercancel', finish);
        }
        setupDialogDroplet();

        // ============ PAGE-END SPRING BOUNCE (overscroll) ============
        // When a view is scrolled to its very end (or very top) and the user keeps
        // pulling, the whole page does a soft spring bounce.
        (function () {
            const SKIND = 8, BOUNCE_MS = 420;
            let wrap = null, busy = false, acc = 0, lastY = null, tracking = false;
            function scrollEl() {
                return document.scrollingElement || document.documentElement;
            }
            document.addEventListener('touchstart', function (e) {
                if (busy) return;
                acc = 0; lastY = e.touches[0].clientY; tracking = true;
            }, { passive: true });
            document.addEventListener('touchmove', function (e) {
                if (!tracking || busy) return;
                const y = e.touches[0].clientY;
                acc += (lastY - y); lastY = y;
            }, { passive: true });
            document.addEventListener('touchend', function () {
                if (!tracking) return;
                tracking = false;
                if (busy || Math.abs(acc) < SKIND) return;
                const se = scrollEl();
                const atBottom = se.scrollTop + se.clientHeight >= se.scrollHeight - 2;
                const atTop = se.scrollTop <= 2;
                if ((acc < 0 && atBottom) || (acc > 0 && atTop)) {
                    busy = true;
                    wrap = document.getElementById('app-wrapper');
                    if (wrap) {
                        wrap.style.animation = (acc < 0 ? 'pageBounceBottom ' : 'pageBounceTop ') + BOUNCE_MS + 'ms var(--anim-spring)';
                        setTimeout(function () { if (wrap) wrap.style.animation = ''; busy = false; }, BOUNCE_MS + 30);
                    } else { busy = false; }
                }
            });
        })();

        function selectItem(value, ev) {
            ev.stopPropagation();
            const prev = document.getElementById(`val-${activeDialogType}`).innerText;
            document.getElementById(`val-${activeDialogType}`).innerText = value;
            if (activeDialogType === 'dialogAnim') dialogAnimStyle = value;
            if (activeDialogType === 'navSize') applyNavSize(value);
            const items = document.querySelectorAll('.dialog-item');
            items.forEach(el => el.classList.remove('selected'));
            ev.currentTarget.classList.add('selected');
            if (activeDialogType === 'market' && prev !== value) onMarketChanged(value);
            if (activeDialogType === 'timeframe' && prev !== value) onTimeframeChanged(value);
            if (activeDialogType === 'signalMode') onSignalModeChanged(value);
            if (activeDialogType === 'chartStyle' || activeDialogType === 'chartType') setTimeout(function(){ chartResize(); requestDraw(); }, 80);
            if (activeDialogType === 'chartType' && prev !== value) setTimeout(chartResize, 100);
            setTimeout(closeDialog, 250);
            saveSettings();
        }

        function onSignalModeChanged(mode, silent) {
            const autoMarketsItem = document.getElementById('autoMarketsItem');
            if (mode === 'Auto') { autoMarketsItem.style.display = 'flex'; } else { autoMarketsItem.style.display =
                'none'; if (!silent) stopAutoMode(); }
            lucide.createIcons();
            if (!silent) saveSettings();
        }

        function toggleSwitch(element) {
            const toggle = element.querySelector('.toggle');
            if (toggle) toggle.classList.toggle('active');
            saveSettings();
        }

        // ======================== NAV BAR SIZE SETTING ========================
        function applyNavSize(v, silent) {
            document.body.classList.toggle('nav-compact', v === 'Small');
            if (!silent) saveSettings();
        }
        window.applyNavSize = applyNavSize;


        // iOS-style slider live fill (delegated, capture-phase — no handler conflicts)
        function updateRangeFill(el) {
            if (!el || el.type !== 'range') return;
            const min = parseFloat(el.min) || 0;
            const max = parseFloat(el.max);
            if (isNaN(max)) return;
            const val = parseFloat(el.value);
            if (isNaN(val)) return;
            const pct = ((val - min) / (max - min)) * 100;
            el.style.setProperty('--fill', pct + '%');
        }
        document.addEventListener('input', function (e) {
            if (e.target && e.target.type === 'range') updateRangeFill(e.target);
        }, true);
        document.addEventListener('change', function (e) {
            if (e.target && e.target.type === 'range') updateRangeFill(e.target);
        }, true);

        function updateAnimSpeed(v) {
            document.documentElement.style.setProperty('--anim-speed', v);
            document.documentElement.style.setProperty('--speed-multiplier', v);
            const el = document.getElementById('speedVal');
            if (el) el.textContent = parseFloat(v).toFixed(1) + 'x';
            try { localStorage.setItem('ht_anim_speed', v); } catch(e){}
        }
        function updateGlassBlur(v) {
            document.documentElement.style.setProperty('--glass-blur', v + 'px');
            const el = document.getElementById('blurVal');
            if (el) el.textContent = v + 'px';
            updateRangeFill(document.getElementById('blurSlider'));
            try { localStorage.setItem('ht_glass_blur', v); } catch(e){}
        }
        function updateGlassOpacity(v) {
            document.documentElement.style.setProperty('--glass-opacity', v);
            document.documentElement.style.setProperty('--glass-alpha', v);
            const el = document.getElementById('glassVal');
            if (el) el.textContent = Math.round(parseFloat(v) * 100) + '%';
            try { localStorage.setItem('ht_glass_opacity', v); } catch(e){}
        }
        function updateIndicatorGlow(v) {
            document.documentElement.style.setProperty('--indicator-glow', v);
            const el = document.getElementById('glowVal');
            if (el) el.textContent = Math.round(parseFloat(v) * 100) + '%';
            try { localStorage.setItem('ht_indicator_glow', v); } catch(e){}
        }
        function updateFontSize(v) {
            document.documentElement.style.setProperty('--font-base', v + 'px');
            const el = document.getElementById('fontVal');
            if (el) el.textContent = v + 'px';
            updateRangeFill(document.getElementById('fontSlider'));
            try { localStorage.setItem('ht_font_size', v); } catch(e){}
        }
        (function restoreGlassSettings() {
            try {
                const s = localStorage.getItem('ht_anim_speed');
                const b = localStorage.getItem('ht_glass_blur');
                const o = localStorage.getItem('ht_glass_opacity');
                const g = localStorage.getItem('ht_indicator_glow');
                const f = localStorage.getItem('ht_font_size');
                if (s) { const sl = document.getElementById('speedSlider'); if (sl) { sl.value = s; updateAnimSpeed(s); } }
                if (b) { const sl = document.getElementById('blurSlider'); if (sl) { sl.value = b; updateGlassBlur(b); } }
                if (o) { const sl = document.getElementById('glassSlider'); if (sl) { sl.value = o; updateGlassOpacity(o); } }
                if (g) { const sl = document.getElementById('glowSlider'); if (sl) { sl.value = g; updateIndicatorGlow(g); } }
                if (f) { const sl = document.getElementById('fontSlider'); if (sl) { sl.value = f; updateFontSize(f); } }
            } catch(e){}
        })();

        function toggleDarkMode(element) {
            const toggle = element.querySelector('.toggle');
            toggle.classList.toggle('active');
            document.body.classList.toggle('dark-mode', toggle.classList.contains('active'));
            saveSettings();
        }

        // ======================== SLIDERS & INPUTS ========================
        document.getElementById('speedSlider').addEventListener('input', function(e) {
            const val = parseFloat(e.target.value);
            document.documentElement.style.setProperty('--speed-multiplier', val);
            document.getElementById('speedVal').innerText = val.toFixed(1) + 'x';
            saveSettings();
        });
        document.getElementById('glassSlider').addEventListener('input', function(e) {
            const val = parseFloat(e.target.value);
            document.documentElement.style.setProperty('--glass-alpha', val);
            document.getElementById('glassVal').innerText = Math.round(val * 100) + '%';
            saveSettings();
        });
        document.getElementById('fontSlider').addEventListener('input', function(e) {
            const val = e.target.value + 'px';
            document.documentElement.style.fontSize = val;
            document.getElementById('fontVal').innerText = val;
            saveSettings();
        });

        document.getElementById('signalNameInput').addEventListener('input', function() { saveSettings(); });
        document.getElementById('dashboardNameInput').addEventListener('input', function() {
            document.documentElement.style.setProperty('--dashboard-name', '"' + this.value + '"');
            saveSettings();
        });
        document.getElementById('watermarkInput').addEventListener('input', function() {
            document.getElementById('watermarkPreview').innerText = this.value;
            document.documentElement.style.setProperty('--watermark-text', '"' + this.value + '"');
            requestDraw();
            saveSettings();
        });
        document.querySelectorAll('.telegram-input').forEach(el => {
            el.addEventListener('change', saveSettings);
            el.addEventListener('input', saveSettings);
        });

        function resetAll() {
            document.getElementById('val-market').innerText = 'USDBDT-OTC';
            document.getElementById('val-timeframe').innerText = '1 Minute';
            document.getElementById('val-strategy').innerText = 'AI Smart Signal';
            document.getElementById('val-chartType').innerText = 'Candlestick';
            document.getElementById('val-martingale').innerText = 'No MTG';
            document.getElementById('val-dialogAnim').innerText = 'Scale';
            document.getElementById('val-signalMode').innerText = 'Manual';
            document.getElementById('telegramInput').value = '@Mahabub_iX';
            document.getElementById('botTokenInput').value = '';
            document.getElementById('chatIdInput').value = '';
            dialogAnimStyle = 'Scale';
            selectedAutoMarkets = [...ALL_MARKETS];
            document.getElementById('val-autoMarkets').innerText = 'All';
            document.getElementById('autoMarketsItem').style.display = 'none';
            document.getElementById('signalNameInput').value = 'RAVITH AI PRO';
            document.getElementById('dashboardNameInput').value = 'RAVITH PRO';
            document.documentElement.style.setProperty('--dashboard-name', '"RAVITH PRO"');
            document.getElementById('watermarkInput').value = '𝐑𝐀𝐕𝐈𝐓𝐇 𝐒𝐒';
            document.getElementById('watermarkPreview').innerText = '𝐑𝐀𝐕𝐈𝐓𝐇 𝐒𝐒';
            document.documentElement.style.setProperty('--watermark-text', '"𝐑𝐀𝐕𝐈𝐓𝐇 𝐒𝐒"');
            const soundToggle = document.querySelector('[data-toggle-key="soundAlerts"]');
            const vibToggle = document.querySelector('[data-toggle-key="vibration"]');
            if (soundToggle) soundToggle.classList.add('active');
            if (vibToggle) vibToggle.classList.add('active');
            document.getElementById('darkModeToggle').classList.remove('active');
            document.body.classList.remove('dark-mode');
            document.getElementById('autoTelegramToggle').classList.add('active');
            document.getElementById('speedSlider').value = 2;
            document.documentElement.style.setProperty('--speed-multiplier', 2);
            document.getElementById('speedVal').innerText = '2.0x';
            document.getElementById('glassSlider').value = 0.8;
            document.documentElement.style.setProperty('--glass-alpha', 0.8);
            document.getElementById('glassVal').innerText = '80%';
            document.getElementById('fontSlider').value = 12;
            document.documentElement.style.fontSize = '12px';
            document.getElementById('fontVal').innerText = '12px';
            const resetNs = document.getElementById('val-navSize');
            if (resetNs) resetNs.innerText = 'Small';
            document.body.classList.remove('nav-compact');
            resetResult();
            onMarketChanged('USDBDT-OTC');
            saveSettings();
        }

        // ======================== CHART ENGINE ========================
        const canvas = document.getElementById("chart");
        const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
        const W = 600,
            H = 337.5;

        let candles = [],
            allCandles = [],
            liveCandle = null;
        let currentPair = "USDBDT-OTC";
        let currentApiPair = "USDBDT_otc";
        let currentPayout = 0;
        let latestClosePrice = 0;
        let apiError = null;

        const C = { bg: "#050508", green: "#00FF66", greenBright: "#33FF99", red: "#FF3366", redBright: "#FF5C8A",
            yellow: "#FFCC00", yellowBright: "#FFE64D", cyan: "#00F2FE", blue: "#4FACFE", blue2: "#1a3a6c",
            white: "#F4F7FF", gray: "#7A889B", darkGray: "#141923", grid: "rgba(110,140,160,.12)" };

        let _drawScheduled = false;

        function requestDraw() {
            if (_drawScheduled) return;
            _drawScheduled = true;
            requestAnimationFrame(() => {
                _drawScheduled = false;
                draw();
            });
        }

        let resizeTimer = null;

        function chartResize() {
            const rect = canvas.getBoundingClientRect();
            if (rect.width < 2 || rect.height < 2) return;
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            canvas.width = Math.max(1, Math.round(rect.width * dpr));
            canvas.height = Math.max(1, Math.round(rect.height * dpr));
            const scaleX = canvas.width / W,
                scaleY = canvas.height / H;
            ctx.setTransform(scaleX, 0, 0, scaleY, 0, 0);
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";
            requestDraw();
        }
        window.addEventListener("resize", () => { clearTimeout(resizeTimer);
            resizeTimer = setTimeout(chartResize, 80); });

        function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

        function roundRect(x, y, w, h, r) { const rr = Math.min(r, w / 2, h / 2);
            ctx.beginPath();
            ctx.moveTo(x + rr, y);
            ctx.arcTo(x + w, y, x + w, y + h, rr);
            ctx.arcTo(x + w, y + h, x, y + h, rr);
            ctx.arcTo(x, y + h, x, y, rr);
            ctx.arcTo(x, y, x + w, y, rr);
            ctx.closePath(); }

        function text(value, x, y, size, color, align = "left", weight = "normal") { ctx.font =
                `${weight} ${size}px monospace`;
            ctx.fillStyle = color;
            ctx.textAlign = align;
            ctx.textBaseline = "middle";
            ctx.fillText(value, x, y); }

        function panel(x, y, w, h, glowColor = "rgba(0,242,254,.35)") { ctx.save(); const grad = ctx.createLinearGradient(x,
                y, x, y + h);
            grad.addColorStop(0, "rgba(10,18,35,0.94)");
            grad.addColorStop(1, "rgba(5,10,20,0.97)");
            ctx.fillStyle = grad;
            ctx.strokeStyle = "rgba(0,242,254,0.45)";
            ctx.lineWidth = 1;
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = 6;
            roundRect(x, y, w, h, 3);
            ctx.fill();
            ctx.stroke();
            ctx.restore(); }

        function neonLine(points, color, width = 1) { if (!points || points.length < 2) return;
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.shadowColor = color;
            ctx.shadowBlur = 4;
            ctx.stroke();
            ctx.restore(); }

        function priceFormat(v) { return Number(v).toFixed(5); }

        function timeFormat(v) { if (!v) return ""; if (v.length >= 16) return v.substring(11, 16); return v; }

        function calculateEMA(data, period) { if (!data.length) return [];
            const k = 2 / (period + 1);
            let ema = data[0].close;
            const out = [ema];
            for (let i = 1; i < data.length; i++) { ema = data[i].close * k + ema * (1 - k);
                out.push(ema); }
            return out; }

        function displayPairToApi(displayPair) { if (!displayPair) return "USDBDT_otc"; return displayPair.replace(/-OTC$/i,
                "_otc"); }

        function getChartType() { return document.getElementById('val-chartType').innerText.trim(); }

        // ======================== 26 CHART PHOTO DESIGNS ========================
        function getChartStyle() {
            const el = document.getElementById('val-chartStyle');
            const t = el ? el.innerText.trim() : 'Style 1 - Classic';
            const m = t.match(/Style\s+(\d+)/i);
            const n = m ? parseInt(m[1], 10) : 1;
            return (n >= 1 && n <= 26) ? n : 1;
        }

        const CHART_THEMES = {
            1:  { name:'Classic', bg:'#050508', grid:'rgba(110,140,160,.12)', up:'#00FF66', down:'#FF3366', accent:'#00F2FE', wick:'#F4F7FF', label:'#7A889B', glow:false, neon:false },
            2:  { name:'Terminal', bg:'#0a0e0a', grid:'rgba(0,255,100,.08)', up:'#33ff66', down:'#ff2244', accent:'#00ff88', wick:'#aaffcc', label:'#66aa77', glow:false, neon:true },
            3:  { name:'Futuristic', bg:'#06061a', grid:'rgba(100,120,255,.12)', up:'#00e5ff', down:'#ff2d95', accent:'#7c5cff', wick:'#d0e0ff', label:'#8899cc', glow:true, neon:true },
            4:  { name:'Pro Finance', bg:'#0c1118', grid:'rgba(140,160,180,.10)', up:'#26a69a', down:'#ef5350', accent:'#42a5f5', wick:'#cfd8dc', label:'#90a4ae', glow:false, neon:false },
            5:  { name:'Neon Pulse', bg:'#050510', grid:'rgba(255,0,200,.08)', up:'#39ff14', down:'#ff073a', accent:'#ff00ff', wick:'#ffffff', label:'#ff66cc', glow:true, neon:true },
            6:  { name:'Deep Ocean', bg:'#020b18', grid:'rgba(0,180,255,.10)', up:'#00d4aa', down:'#ff6b6b', accent:'#00b4ff', wick:'#a0e0ff', label:'#5a9ab8', glow:true, neon:false },
            7:  { name:'Sunset Drive', bg:'#12080a', grid:'rgba(255,140,60,.10)', up:'#ffaa00', down:'#ff3355', accent:'#ff6b35', wick:'#ffe0c0', label:'#cc8866', glow:true, neon:false },
            8:  { name:'Royal Violet', bg:'#0c0618', grid:'rgba(180,100,255,.12)', up:'#b388ff', down:'#ff4d6d', accent:'#9c27b0', wick:'#e1bee7', label:'#ba68c8', glow:true, neon:true },
            9:  { name:'Cyber Grid', bg:'#030608', grid:'rgba(0,255,200,.15)', up:'#00ffc8', down:'#ff0055', accent:'#00ffaa', wick:'#ccfff0', label:'#00cc99', glow:false, neon:true },
            10: { name:'Galaxy', bg:'#050510', grid:'rgba(150,120,255,.10)', up:'#7c4dff', down:'#ff4081', accent:'#e040fb', wick:'#f3e5f5', label:'#ce93d8', glow:true, neon:true },
            11: { name:'Matrix', bg:'#000a00', grid:'rgba(0,255,0,.10)', up:'#00ff41', down:'#008f11', accent:'#00ff00', wick:'#00ff41', label:'#00aa00', glow:false, neon:true },
            12: { name:'Aurora', bg:'#041018', grid:'rgba(0,255,180,.10)', up:'#00e676', down:'#ff5252', accent:'#18ffff', wick:'#e0f7fa', label:'#80deea', glow:true, neon:true },
            13: { name:'Golden Bull', bg:'#100c04', grid:'rgba(255,200,50,.10)', up:'#ffd700', down:'#c62828', accent:'#ffc107', wick:'#fff8e1', label:'#ffcc80', glow:true, neon:false },
            14: { name:'Ice Crystal', bg:'#061018', grid:'rgba(180,230,255,.12)', up:'#80d8ff', down:'#ff8a80', accent:'#40c4ff', wick:'#e1f5fe', label:'#81d4fa', glow:true, neon:false },
            15: { name:'Retro Wave', bg:'#0a0414', grid:'rgba(255,0,170,.10)', up:'#ff2a6d', down:'#05d9e8', accent:'#d1f7ff', wick:'#ff71ce', label:'#b967ff', glow:true, neon:true },
            16: { name:'Holo 3D', bg:'#080814', grid:'rgba(200,180,255,.12)', up:'#64ffda', down:'#ff80ab', accent:'#ea80fc', wick:'#ffffff', label:'#b39ddb', glow:true, neon:true },
            17: { name:'Quantum', bg:'#04040c', grid:'rgba(100,255,255,.10)', up:'#18ffff', down:'#ff1744', accent:'#00e5ff', wick:'#e0ffff', label:'#84ffff', glow:true, neon:true },
            18: { name:'Stealth', bg:'#0a0a0a', grid:'rgba(120,120,120,.10)', up:'#76ff03', down:'#ff1744', accent:'#b0bec5', wick:'#eceff1', label:'#78909c', glow:false, neon:false },
            19: { name:'Plasma', bg:'#0c0410', grid:'rgba(255,50,200,.10)', up:'#e040fb', down:'#ff1744', accent:'#ff4081', wick:'#f8bbd0', label:'#f48fb1', glow:true, neon:true },
            20: { name:'Limon Pro', bg:'#050d08', grid:'rgba(50,205,50,.12)', up:'#32CD32', down:'#ff3366', accent:'#00F2FE', wick:'#e8ffe8', label:'#7dcea0', glow:true, neon:true },
            21: { name:'Aurora Q', bg:'#040c14', grid:'rgba(0,242,254,.12)', up:'#00e676', down:'#ff5252', accent:'#00f2fe', wick:'#e0f7fa', label:'#4dd0e1', glow:true, neon:true },
            22: { name:'Cyber Mx', bg:'#020808', grid:'rgba(0,255,170,.14)', up:'#00ff9f', down:'#ff005c', accent:'#00ffc6', wick:'#ccffee', label:'#00c896', glow:false, neon:true },
            23: { name:'Orbital', bg:'#060a12', grid:'rgba(140,180,255,.12)', up:'#4fc3f7', down:'#ef5350', accent:'#82b1ff', wick:'#e3f2fd', label:'#90caf9', glow:true, neon:false },
            24: { name:'Phoenix', bg:'#100505', grid:'rgba(255,80,40,.12)', up:'#ff6d00', down:'#d50000', accent:'#ff3d00', wick:'#ffccbc', label:'#ff8a65', glow:true, neon:true },
            25: { name:'Nexus', bg:'#05070f', grid:'rgba(0,200,255,.12)', up:'#00e5ff', down:'#ff1744', accent:'#2979ff', wick:'#e1f5fe', label:'#40c4ff', glow:true, neon:true },
            26: { name:'Quantum Glass', bg:'#04060d', grid:'rgba(160,220,255,.14)', up:'#32CD32', down:'#ff5566', accent:'#00f2fe', wick:'#e8f7ff', label:'#93c5fd', glow:true, neon:true }
        };

        function applyChartTheme(th) {
            C.bg = th.bg; C.grid = th.grid; C.green = th.up; C.red = th.down;
            C.cyan = th.accent; C.white = th.wick; C.gray = th.label;
            C.greenBright = th.up; C.redBright = th.down; C.yellow = th.accent;
        }



        let liveTickInterval = null;
        let livePollInterval = null;
        let loadInFlight = false;
        let livePollInFlight = false;
        let lastRunningKey = null;
        let lastRunningTime = null;

        function mapCandle(c) {
            return {
                open: Number(c.open), high: Number(c.high), low: Number(c.low), close: Number(c.close),
                volume: Number(c.volume || c.Volume || 0),
                signal: String(c.signal || '').trim().toUpperCase(),
                payout: Number(c.payout || 0), time: c.time || '', pair: c.pair || '',
                is_running: !!c.is_running, ticks: Number(c.ticks || 0)
            };
        }

        function applyRunningCandle(running) {
            if (!running) return false;
            const rc = mapCandle(running);
            if (!Number.isFinite(rc.open) || !Number.isFinite(rc.close)) return false;
            if (engine.currentSignal && engine.state !== 'idle' && engine.state !== 'resolved') {
                rc.signal = engine.currentSignal.direction;
            } else if (liveCandle && liveCandle.signal && liveCandle.time === rc.time) {
                rc.signal = liveCandle.signal;
            }
            rc._initialized = true;
            rc._fromQuotex = true;
            rc.is_running = true;

            // Minute rollover: promote previous running candle into closed history
            if (lastRunningTime && rc.time && rc.time !== lastRunningTime && liveCandle && liveCandle._fromQuotex) {
                const promoted = {
                    open: liveCandle.open, high: liveCandle.high, low: liveCandle.low, close: liveCandle.close,
                    signal: liveCandle.signal || '', payout: liveCandle.payout || 0,
                    time: liveCandle.time, pair: liveCandle.pair
                };
                if (!candles.length || candles[candles.length - 1].time !== promoted.time) {
                    candles.push(promoted);
                    if (candles.length > 40) candles = candles.slice(-40);
                    allCandles.push(promoted);
                }
            }

            liveCandle = rc;
            latestClosePrice = rc.close;
            lastRunningKey = rc.time + '|' + rc.close + '|' + rc.ticks;
            lastRunningTime = rc.time;
            return true;
        }

        // NO simulated ticks — chart uses ONLY real Quotex running candle
        function simulateLiveTick() {
            if (liveCandle && liveCandle._fromQuotex) requestDraw();
        }

        async function pollLiveRunning() {
            if (!currentApiPair || livePollInFlight) return;
            livePollInFlight = true;
            try {
                const url = API_BASE + '/latest?Pair=' + encodeURIComponent(currentApiPair) + '&Time=1m';
                const response = await fetch(url, { cache: 'no-store' });
                if (!response.ok) throw new Error('live ' + response.status);
                const json = await response.json();
                if (applyRunningCandle(json.running)) {
                    apiError = null;
                    setChartStatus('LIVE', 'ok');
                    evaluateWaitingResult();
                    requestDraw();
                } else if (json.data && (!liveCandle || !liveCandle._fromQuotex)) {
                    const last = mapCandle(json.data);
                    liveCandle = Object.assign({}, last, { _initialized: true, _fromQuotex: false, is_running: false });
                    latestClosePrice = last.close;
                    requestDraw();
                }
            } catch (e) {
            } finally {
                livePollInFlight = false;
            }
        }

        function startLiveTicks() {
            if (livePollInterval) clearInterval(livePollInterval);
            livePollInterval = setInterval(function () {
                if (currentApiPair) pollLiveRunning();
            }, 500);
            pollLiveRunning();
            if (liveTickInterval) clearInterval(liveTickInterval);
            liveTickInterval = setInterval(function () { if (liveCandle) requestDraw(); }, 1000);
        }

        function stopLiveTicks() {
            if (liveTickInterval) { clearInterval(liveTickInterval); liveTickInterval = null; }
            if (livePollInterval) { clearInterval(livePollInterval); livePollInterval = null; }
        }

        async function loadData(pairApi, quiet) {
            if (!pairApi) return false;
            if (loadInFlight) return false;
            loadInFlight = true;
            const url = API_BASE + '/?Pair=' + encodeURIComponent(pairApi) + '&Candle=200&Time=1m';
            if (!quiet) setChartStatus('SYNCING', 'ok');
            try {
                const response = await fetch(url, { cache: 'no-store' });
                if (!response.ok) throw new Error('API Error: ' + response.status);
                const json = await response.json();
                if (!json || !Array.isArray(json.data)) throw new Error('Invalid JSON');
                const all = json.data.map(mapCandle).filter(function (c) {
                    return Number.isFinite(c.open) && Number.isFinite(c.high) &&
                        Number.isFinite(c.low) && Number.isFinite(c.close);
                }).reverse();
                if (!all.length) {
                    if (!candles.length) {
                        apiError = 'NO DATA AVAILABLE';
                        setChartStatus(apiError, 'warn');
                        requestDraw();
                    }
                    if (json.running) applyRunningCandle(json.running);
                    loadInFlight = false;
                    return false;
                }
                allCandles = all;
                // Drop closed candle that is still the forming (running) minute
                if (json.running && json.running.time && all.length && all[all.length - 1].time === json.running.time) {
                    all = all.slice(0, -1);
                    allCandles = allCandles.slice(0, -1);
                }
                candles = all.slice(-40);
                const last = all.length ? all[all.length - 1] : null;
                if (last) latestClosePrice = last.close;
                const hasRunning = applyRunningCandle(json.running);
                if (!hasRunning && last) {
                    if (!liveCandle || !liveCandle._fromQuotex) {
                        liveCandle = {
                            open: last.close, high: last.close, low: last.close, close: last.close,
                            time: last.time, pair: last.pair,
                            signal: (engine.currentSignal && engine.state !== 'idle') ? engine.currentSignal.direction : '',
                            _initialized: true, _fromQuotex: false, is_running: false
                        };
                    }
                }
                
                const payoutSample = all.slice(-30).map(function (c) { return c.payout; }).filter(function (p) { return p > 0; });
                currentPayout = payoutSample.length
                    ? Math.round(payoutSample.reduce(function (a, b) { return a + b; }, 0) / payoutSample.length) : 0;
                apiError = null;
                setChartStatus('LIVE', 'ok');
                evaluateWaitingResult();
                requestDraw();
                loadInFlight = false;
                return true;
            } catch (err) {
                console.error('Chart API Error:', err);
                if (!quiet || !candles.length) {
                    apiError = 'API CONNECTION ERROR';
                    setChartStatus(apiError, 'err');
                    requestDraw();
                }
                loadInFlight = false;
                return false;
            }
        }

        function setChartStatus(txt, level) {
            const box = document.getElementById('chartStatus');
            const txtEl = document.getElementById('chartStatusText');
            if (!box) return;
            box.classList.remove('err', 'warn');
            if (level === 'err') box.classList.add('err');
            else if (level === 'warn') box.classList.add('warn');
            if (txt === 'LIVE' && liveCandle && liveCandle._fromQuotex) {
                txtEl.innerText = 'LIVE' + (liveCandle.ticks ? (' · ' + liveCandle.ticks + 't') : '');
            } else {
                txtEl.innerText = txt;
            }
        }

        // ======================== CHART RENDERING (FULL UI ALWAYS) ========================
        function draw() {
            ctx.save();
            ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
            ctx.clearRect(0, 0, W, H);
            ctx.fillStyle = C.bg;
            ctx.fillRect(0, 0, W, H);
            ctx.strokeStyle = "rgba(0,242,254,.3)";
            ctx.lineWidth = 1;
            ctx.strokeRect(1, 1, W - 2, H - 2);
            drawHeader();
            if (apiError) { drawErrorState();
                ctx.restore(); return; }
            if (!candles.length) { drawLoadingState();
                ctx.restore(); return; }
            const chartType = getChartType();
            const styleNum = getChartStyle();
            const th = CHART_THEMES[styleNum] || CHART_THEMES[1];
            applyChartTheme(th);
            drawMainChart(chartType);
            // Style badge
            try {
                ctx.save();
                ctx.font = 'bold 6px JetBrains Mono, monospace';
                ctx.fillStyle = th.accent;
                ctx.globalAlpha = 0.85;
                ctx.textAlign = 'left';
                ctx.fillText('S' + styleNum + ' · ' + th.name, 8, H - 8);
                ctx.restore();
            } catch (e) {}
            drawDashboard();
            drawExpiryPanel();
            drawBottomBar();
            drawWatermark();
            ctx.restore();
        }

        function drawLoadingState() { text("◈ LOADING MARKET DATA...", W / 2, H / 2, 8, "#00F2FE", "center", "bold"); }

        function drawErrorState() { text("⚠ " + apiError, W / 2, H / 2 - 6, 10, "#FF3366", "center", "bold");
            text("Retrying automatically…", W / 2, H / 2 + 8, 6, "#7A889B", "center", "normal"); }

        function drawHeader() { const pair = currentPair || "USDBDT-OTC";
            text(pair.toUpperCase() + " • M1 PRO", 6, 9, 5.5, "#00F2FE", "left", "bold"); }

        function drawMainChart(chartType) {
            if (!candles.length) return;
            const chartLeft = -4,
                chartRight = W - 35,
                chartTop = 4,
                chartBottom = H - 52;
            const chartW = chartRight - chartLeft,
                chartH = chartBottom - chartTop;
            const displayData = liveCandle ? [...candles, liveCandle] : candles;
            let plotData = displayData;
            if (chartType === 'Heikin Ashi') { plotData = [];
                let prevHA = null; for (let i = 0; i < displayData.length; i++) { const c = displayData[i]; const haClose =
                        (c.open + c.high + c.low + c.close) / 4; let haOpen; if (i === 0 || !prevHA) { haOpen = (c.open +
                            c.close) / 2; } else { haOpen = (prevHA.open + prevHA.close) / 2; } const haHigh = Math.max(c
                            .high, haOpen, haClose); const haLow = Math.min(c.low, haOpen, haClose); const ha = { open: haOpen,
                            high: haHigh, low: haLow, close: haClose, time: c.time, pair: c.pair, signal: c.signal };
                    plotData.push(ha);
                    prevHA = ha; } }
            let min = Infinity,
                max = -Infinity;
            for (const c of plotData) { min = Math.min(min, c.low);
                max = Math.max(max, c.high); }
            const range = max - min || 0.0001;
            min -= range * .06;
            max += range * .06;

            function priceY(price) { return chartTop + ((max - price) / (max - min)) * chartH; }
            ctx.save();
            ctx.strokeStyle = C.grid;
            ctx.lineWidth = .6;
            for (let i = 0; i <= 10; i++) { const y = chartTop + chartH * i / 10;
                ctx.beginPath();
                ctx.moveTo(chartLeft, y);
                ctx.lineTo(chartRight, y);
                ctx.stroke(); }
            for (let i = 0; i <= 12; i++) { const x = chartLeft + chartW * i / 12;
                ctx.beginPath();
                ctx.moveTo(x, chartTop);
                ctx.lineTo(x, chartBottom);
                ctx.stroke(); }
            ctx.restore();
            const count = plotData.length;
            const spacing = chartW / count;
            const candleWidth = Math.max(5, spacing * .62);
            // Draw EMA (20 period) for EMA strategy or always? We'll draw it always as a guide.
            const ema20 = calculateEMA(plotData, 20);
            const emaPoints = ema20.map((v, i) => ({ x: chartLeft + i * spacing + spacing / 2, y: priceY(v) }));
            neonLine(emaPoints, "#FFCC00", 1.5); // yellow EMA

            // Also draw fast EMA 9 (optional)
            const ema9 = calculateEMA(plotData, 9);
            const ema9Points = ema9.map((v, i) => ({ x: chartLeft + i * spacing + spacing / 2, y: priceY(v) }));
            neonLine(ema9Points, "#00F2FE", 1.5);

            const recent = plotData.slice(Math.max(0, plotData.length - 15));
            const support = Math.min(...recent.map(c => c.low));
            const resistance = Math.max(...recent.map(c => c.high));
            drawHorizontalLevel(priceY(support), "#00FF66", "SUP");
            drawHorizontalLevel(priceY(resistance), "#FF3366", "RES");
            drawTrendLines(chartLeft, chartRight, chartTop, chartBottom);
            if (chartType === 'Candlestick' || chartType === 'Heikin Ashi') { drawCandlesticks(plotData, chartLeft,
                    spacing, candleWidth, priceY); } else if (chartType === 'Line') { drawLineChart(plotData, chartLeft,
                    spacing, priceY); } else if (chartType === 'Area') { drawAreaChart(plotData, chartLeft, spacing,
                    priceY, chartBottom); }
            const lastIdx = plotData.length - 1;
            if (lastIdx >= 0 && engine.currentSignal && engine.state !== 'idle' && engine.state !== 'resolved') {
                const c = plotData[lastIdx];
                const x = chartLeft + lastIdx * spacing + spacing / 2;
                const openY = priceY(c.open),
                    closeY = priceY(c.close);
                const highY = priceY(c.high),
                    lowY = priceY(c.low);
                const top = Math.min(openY, closeY),
                    bottom = Math.max(openY, closeY);
                drawSignalArrow(x, top, bottom, highY, lowY, engine.currentSignal.direction);
            }
            if (liveCandle) { const lastC = plotData[plotData.length - 1]; if (lastC) { const closeY = priceY(lastC
                        .close);
                    ctx.save();
                    ctx.strokeStyle = "#00F2FE";
                    ctx.lineWidth = 0.8;
                    ctx.setLineDash([2, 2]);
                    ctx.beginPath();
                    ctx.moveTo(chartLeft, closeY);
                    ctx.lineTo(chartRight, closeY);
                    ctx.stroke();
                    ctx.setLineDash([]);
                    const secLeft = 60 - new Date().getSeconds();
                    const secFormatted = secLeft < 10 ? '0' + secLeft : secLeft;
                    const x = chartLeft + (plotData.length - 1) * spacing + spacing / 2;
                    text(`⚡ 00:${secFormatted}`, x + candleWidth + 3, closeY, 5.5, "#FFCC00", "left", "bold");
                    ctx.restore(); } }
            drawPriceScale(chartRight, chartTop, chartBottom, min, max);
            drawTimeScale(chartLeft, chartW, chartBottom, spacing, plotData);
        }

        function drawCandlesticks(plotData, chartLeft, spacing, candleWidth, priceY) {
            const th = CHART_THEMES[getChartStyle()] || CHART_THEMES[1];
            for (let i = 0; i < plotData.length; i++) { const c = plotData[i];
                const x = chartLeft + i * spacing + spacing / 2;
                const openY = priceY(c.open),
                    closeY = priceY(c.close);
                const highY = priceY(c.high),
                    lowY = priceY(c.low);
                const bullish = c.close >= c.open;
                ctx.save();
                if (th.glow || th.neon) {
                    ctx.shadowColor = bullish ? th.up : th.down;
                    ctx.shadowBlur = th.neon ? 8 : 4;
                }
                ctx.strokeStyle = bullish ? "#00FF66" : "#FF3366";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(x, highY);
                ctx.lineTo(x, lowY);
                ctx.stroke();
                ctx.restore();
                const top = Math.min(openY, closeY),
                    bottom = Math.max(openY, closeY);
                const bodyH = Math.max(bottom - top, 2);
                ctx.fillStyle = "rgba(0,0,0,.85)";
                ctx.fillRect(x - candleWidth / 2 + 2, top + 2, candleWidth, bodyH);
                const grad = ctx.createLinearGradient(x - candleWidth / 2, 0, x + candleWidth / 2, 0);
                if (bullish) { grad.addColorStop(0, "#009933");
                    grad.addColorStop(.5, "#00FF66");
                    grad.addColorStop(1, "#008822"); } else { grad.addColorStop(0, "#990022");
                    grad.addColorStop(.5, "#FF3366");
                    grad.addColorStop(1, "#880011"); }
                ctx.fillStyle = grad;
                ctx.fillRect(x - candleWidth / 2, top, candleWidth, bodyH);
                ctx.strokeStyle = bullish ? "#33FF99" : "#FF6688";
                ctx.lineWidth = .5;
                ctx.strokeRect(x - candleWidth / 2, top, candleWidth, bodyH); }
        }

        function drawLineChart(plotData, chartLeft, spacing, priceY) { ctx.save();
            ctx.beginPath();
            for (let i = 0; i < plotData.length; i++) { const x = chartLeft + i * spacing + spacing / 2;
                const y = priceY(plotData[i].close); if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y); }
            ctx.strokeStyle = "#00F2FE";
            ctx.lineWidth = 2;
            ctx.shadowColor = "#00F2FE";
            ctx.shadowBlur = 8;
            ctx.stroke();
            ctx.restore();
            for (let i = 0; i < plotData.length; i += 2) { const x = chartLeft + i * spacing + spacing / 2;
                const y = priceY(plotData[i].close);
                ctx.save();
                ctx.fillStyle = "#00F2FE";
                ctx.shadowColor = "#00F2FE";
                ctx.shadowBlur = 4;
                ctx.beginPath();
                ctx.arc(x, y, 1.5, 0, Math.PI * 2);
                ctx.fill();
                ctx.restore(); } }

        function drawAreaChart(plotData, chartLeft, spacing, priceY, chartBottom) { ctx.save();
            ctx.beginPath();
            for (let i = 0; i < plotData.length; i++) { const x = chartLeft + i * spacing + spacing / 2;
                const y = priceY(plotData[i].close); if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y); }
            ctx.lineTo(chartLeft + (plotData.length - 1) * spacing + spacing / 2, chartBottom);
            ctx.lineTo(chartLeft + spacing / 2, chartBottom);
            ctx.closePath();
            const grad = ctx.createLinearGradient(0, 4, 0, chartBottom);
            grad.addColorStop(0, "rgba(0,242,254,0.3)");
            grad.addColorStop(1, "rgba(0,242,254,0.02)");
            ctx.fillStyle = grad;
            ctx.fill();
            ctx.strokeStyle = "#00F2FE";
            ctx.lineWidth = 2;
            ctx.shadowColor = "#00F2FE";
            ctx.shadowBlur = 8;
            ctx.stroke();
            ctx.restore(); }

        function drawSignalArrow(x, top, bottom, highY, lowY, direction) {
            const isBuy = direction === "BUY" || direction === "CALL";
            const isSell = direction === "SELL" || direction === "PUT";
            if (!isBuy && !isSell) return;
            const arrowSize = 10,
                offset = 6;
            ctx.save();
            ctx.shadowColor = "#FFCC00";
            ctx.shadowBlur = 16;
            ctx.fillStyle = "#FFCC00";
            if (isBuy) { const tipY = lowY + offset,
                    baseY = tipY + arrowSize;
                ctx.beginPath();
                ctx.moveTo(x, tipY);
                ctx.lineTo(x - 5, baseY - 3);
                ctx.lineTo(x - 2, baseY - 2);
                ctx.lineTo(x - 2, baseY + 2);
                ctx.lineTo(x + 2, baseY + 2);
                ctx.lineTo(x + 2, baseY - 2);
                ctx.lineTo(x + 5, baseY - 3);
                ctx.closePath();
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.fillStyle = "#FFCC00";
                ctx.font = "bold 5px monospace";
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                ctx.fillText("BUY", x, baseY + 3); } else { const tipY = highY - offset,
                    baseY = tipY - arrowSize;
                ctx.beginPath();
                ctx.moveTo(x, tipY);
                ctx.lineTo(x - 5, baseY + 3);
                ctx.lineTo(x - 2, baseY + 2);
                ctx.lineTo(x - 2, baseY - 2);
                ctx.lineTo(x + 2, baseY - 2);
                ctx.lineTo(x + 2, baseY + 2);
                ctx.lineTo(x + 5, baseY + 3);
                ctx.closePath();
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.fillStyle = "#FFCC00";
                ctx.font = "bold 5px monospace";
                ctx.textAlign = "center";
                ctx.textBaseline = "bottom";
                ctx.fillText("SELL", x, baseY - 3); }
            ctx.restore();
        }

        function drawHorizontalLevel(y, color, label) { ctx.save();
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.shadowColor = color;
            ctx.shadowBlur = 3;
            ctx.beginPath();
            ctx.moveTo(2, y);
            ctx.lineTo(W - 35, y);
            ctx.stroke();
            text(label, W - 145, y + 7, 4.5, color, "left", "bold");
            ctx.restore(); }

        function drawTrendLines(left, right, top, bottom) {
            ctx.save();
            ctx.strokeStyle = "rgba(0,242,254,.25)";
            ctx.lineWidth = .7;
            ctx.beginPath();
            ctx.moveTo(left + W * .28, top);
            ctx.lineTo(right, top + bottom * .55);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(left + W * .36, top);
            ctx.lineTo(right, bottom - 70);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(left + W * .62, bottom);
            ctx.lineTo(right, bottom * .40);
            ctx.stroke();
            ctx.restore();
        }

        function drawPriceScale(x, top, bottom, min, max) { for (let i = 0; i < 11; i++) { const ratio = i / 10,
                    y = top + (bottom - top) * ratio;
                const price = max - (max - min) * ratio;
                text(priceFormat(price), x + 3, y, 4.5, "#00F2FE", "left", "normal"); } }

        function drawTimeScale(left, width, bottom, spacing, data) { if (!data.length) return;
            const step = Math.max(1, Math.floor(data.length / 10));
            for (let i = 0; i < data.length; i += step) { const c = data[i],
                    x = left + i * spacing + spacing / 2;
                text(timeFormat(c.time), x, bottom + 16, 4, "#7A889B", "center", "normal"); } }

        function drawDashboard() {
            const x = 10,
                y = 10,
                w = 126,
                h = 122;
            panel(x, y, w, h, "rgba(0,242,254,.4)");
            const headerH = 15;
            const headGrad = ctx.createLinearGradient(x + 4, y + 4, x + w - 4, y + 4);
            headGrad.addColorStop(0, "#0c2545");
            headGrad.addColorStop(1, "#134074");
            ctx.fillStyle = headGrad;
            roundRect(x + 4, y + 4, w - 8, headerH, 2);
            ctx.fill();
            const dashName = document.getElementById('dashboardNameInput').value || "RAVITH PRO";
            text("◈ " + dashName.toUpperCase(), x + 7, y + 4 + headerH / 2, 5.5, "#00F2FE", "left", "bold");
            text("AI-V8", x + w - 7, y + 4 + headerH / 2, 4.5, "#FFCC00", "right", "bold");
            const wins = engine.stats.wins,
                losses = engine.stats.losses;
            const total = wins + losses,
                rate = total ? Math.round(wins / total * 100) : 0;
            const statY = y + 30;
            text(String(wins), x + 7, statY, 9.5, "#00FF66", "left", "bold");
            text(String(losses), x + 56, statY, 9.5, "#FF3366", "left", "bold");
            text(rate + "%", x + 98, statY, 9.5, "#F4F7FF", "left", "bold");
            const labelY = statY + 8;
            text("✓ WIN", x + 7, labelY, 3.8, "#33FF99", "left", "bold");
            text("× LOSS", x + 56, labelY, 3.8, "#FF6688", "left", "bold");
            text("GRADE", x + 98, labelY, 3.8, "#7A889B", "left", "bold");
            const progY = labelY + 6;
            ctx.fillStyle = "#141923";
            roundRect(x + 7, progY, w - 14, 3.5, 1.5);
            ctx.fill();
            const ratePct = total ? clamp(rate / 100, 0, 1) : 0;
            const barGrad = ctx.createLinearGradient(x + 7, 0, x + 7 + (w - 14), 0);
            barGrad.addColorStop(0, "#00FF66");
            barGrad.addColorStop(1, "#00F2FE");
            ctx.fillStyle = barGrad;
            roundRect(x + 7, progY, (w - 14) * ratePct, 3.5, 1.5);
            ctx.fill();
            const row1Y = progY + 10;
            text("▸ SIGNALS", x + 7, row1Y, 4.5, "#7A889B", "left", "normal");
            text(String(total), x + w - 7, row1Y, 5.5, "#F4F7FF", "right", "bold");
            const row2Y = row1Y + 8;
            text("▸ STREAK", x + 7, row2Y, 4.5, "#7A889B", "left", "normal");
            text(String(engine.stats.streakW) + "W", x + w - 21, row2Y, 5.5, "#00FF66", "right", "bold");
            text(String(engine.stats.streakL) + "L", x + w - 7, row2Y, 5.5, "#FF3366", "right", "bold");
            const row3Y = row2Y + 8;
            text("▸ TREND", x + 7, row3Y, 4.5, "#7A889B", "left", "normal");
            const trend = candles.length >= 5 ? candles[candles.length - 1].close > candles[candles.length - 5].close ?
                "BULLISH" : "BEARISH" : "WAIT";
            text(trend, x + w - 7, row3Y, 5.5, trend === "BULLISH" ? "#00FF66" : trend === "BEARISH" ? "#FF3366" :
                "#FFCC00", "right", "bold");
            const buttons = [
                ["M1", "#00FF66"],
                ["M5", "#4FACFE"],
                ["M15", "#4FACFE"],
                ["M30", "#4FACFE"],
                ["H1", "#4FACFE"],
                ["D1", "#4FACFE"]
            ];
            const btnY = row3Y + 8,
                btnW = 15,
                btnH = 10;
            let bx = x + 7;
            const btnSpacing = (w - 14 - btnW * buttons.length) / (buttons.length - 1);
            for (const b of buttons) { ctx.fillStyle = b[0] === "M1" ? "rgba(0,255,102,.15)" : "#0c1628";
                ctx.strokeStyle = b[0] === "M1" ? "#00FF66" : "#1a3a6c";
                ctx.lineWidth = 0.8;
                roundRect(bx, btnY, btnW, btnH, 2);
                ctx.fill();
                ctx.stroke();
                text(b[0], bx + btnW / 2, btnY + btnH / 2, 4, b[1], "center", "bold");
                bx += btnW + btnSpacing; }
            const recent20 = candles.slice(-20);
            const bulls = recent20.filter(c => c.close >= c.open).length;
            const buyPct = recent20.length ? Math.round(bulls / recent20.length * 100) : 50;
            const sellPct = 100 - buyPct;
            const bsY = btnY + 14;
            text("BUY " + buyPct + "%", x + 7, bsY, 4.5, "#00FF66", "left", "bold");
            text("SELL " + sellPct + "%", x + w - 7, bsY, 4.5, "#FF3366", "right", "bold");
            const barY = bsY + 4;
            ctx.fillStyle = "#141923";
            roundRect(x + 7, barY, w - 14, 3, 1);
            ctx.fill();
            ctx.fillStyle = "#00FF66";
            roundRect(x + 7, barY, (w - 14) * (buyPct / 100), 3, 1);
            ctx.fill();
            const telY = barY + 9;
            text("⚡ LIVE SYNC", x + 7, telY, 4.5, "#00F2FE", "left", "bold");
            const clock = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit",
                hour12: false });
            text(clock, x + w - 7, telY, 5.5, "#FFCC00", "right", "bold");
        }

        function drawExpiryPanel() {
            const w = 105,
                h = 42,
                x = W - w - 10,
                y = 10;
            panel(x, y, w, h, "rgba(79,172,254,.3)");
            text("⚡ EXPIRY ENGINE", x + w / 2, y + 7, 4.2, "#4FACFE", "center", "bold");
            const items = [
                ["M1", "#00F2FE"],
                ["M2", "#00F2FE"],
                ["M3", "#FFCC00"],
                ["M5", "#B19CD9"]
            ];
            const btnW = 19,
                btnH = 11,
                btnY = y + 13;
            let bx = x + 7;
            const btnSpacing = (w - 14 - btnW * items.length) / (items.length - 1);
            for (let i = 0; i < items.length; i++) { const active = i === 0;
                ctx.fillStyle = active ? "#00F2FE" : "#0c1628";
                ctx.strokeStyle = active ? "#33FF99" : "#1a3a6c";
                ctx.lineWidth = 0.8;
                roundRect(bx, btnY, btnW, btnH, 2);
                ctx.fill();
                ctx.stroke();
                text(items[i][0], bx + btnW / 2, btnY + btnH / 2, 4, active ? "#050508" : items[i][1], "center", "bold");
                bx += btnW + btnSpacing; }
            const futY = btnY + btnH + 4,
                futH = 11;
            const futGrad = ctx.createLinearGradient(x + 7, futY, x + 7 + (w - 14), futY);
            futGrad.addColorStop(0, "#1f1700");
            futGrad.addColorStop(1, "#332600");
            ctx.fillStyle = futGrad;
            ctx.strokeStyle = "#FFCC00";
            ctx.lineWidth = 0.8;
            roundRect(x + 7, futY, w - 14, futH, 2);
            ctx.fill();
            ctx.stroke();
            text("⭐ QUANTUM SIGNAL", x + w / 2, futY + futH / 2, 4, "#FFCC00", "center", "bold");
        }

        function drawBottomBar() {
            const h = 14,
                y = H - h - 5;
            const items = [
                ["CHART PRO", "70"],
                ["×", "14"],
                ["BUY", "32"],
                ["SELL", "32"],
                ["EXP 01:00", "42"],
                ["➜ SYNC STREAM", "72"],
                [currentPair.toUpperCase().substring(0, 10), "53"],
                ["▣ GUIDE", "45"],
                ["➤ MODE : PRO", "60"]
            ];
            let cursor = 10;
            for (let i = 0; i < items.length; i++) { const width = Number(items[i][1]);
                ctx.fillStyle = "rgba(12,22,40,0.9)";
                ctx.strokeStyle = "rgba(0,242,254,0.3)";
                ctx.lineWidth = 0.8;
                roundRect(cursor, y, width, h, 2);
                ctx.fill();
                ctx.stroke();
                let color = "#F4F7FF";
                if (items[i][0].includes("BUY")) color = "#00FF66";
                if (items[i][0].includes("SELL")) color = "#FF3366";
                if (items[i][0].includes("EXP")) color = "#FFCC00";
                if (items[i][0].includes("SYNC")) color = "#00F2FE";
                text(items[i][0], cursor + width / 2, y + h / 2, 4, color, "center", "bold");
                cursor += width + 3; }
        }

        function drawWatermark() {
            const cx = W * .48,
                cy = H * .43;
            const wmText = document.getElementById('watermarkInput').value || "𝐑𝐀𝐕𝐈𝐓𝐇 𝐒𝐒";
            ctx.save();
            ctx.font = "bold 36px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            for (let i = 5; i >= 1; i--) { ctx.fillStyle = `rgba(0,242,254,${0.04 + i * 0.015})`;
                ctx.fillText(wmText, cx + i * 0.8, cy + i * 0.8); }
            ctx.fillStyle = "rgba(0,242,254,0.12)";
            ctx.fillText(wmText, cx, cy);
            ctx.shadowColor = "#00F2FE";
            ctx.shadowBlur = 20;
            ctx.fillStyle = "rgba(0,242,254,0.04)";
            ctx.fillText(wmText, cx, cy);
            ctx.restore();
        }

        // ======================== SCREENSHOT (FULL UI) ========================
        function getChartScreenshot() {
            return new Promise((resolve) => {
                // Force crisp redraw then capture at 4x HD, lossless PNG, zero noise
                requestDraw();
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        const scale = 4;
                        const hdCanvas = document.createElement('canvas');
                        hdCanvas.width = Math.round(W * scale);
                        hdCanvas.height = Math.round(H * scale);
                        const hdCtx = hdCanvas.getContext('2d', { alpha: false, willReadFrequently: false });
                        // Solid background — no transparency noise
                        hdCtx.imageSmoothingEnabled = false;
                        hdCtx.fillStyle = (CHART_THEMES[getChartStyle()] || CHART_THEMES[1]).bg;
                        hdCtx.fillRect(0, 0, hdCanvas.width, hdCanvas.height);
                        // Draw source canvas pixel-perfect scaled
                        hdCtx.imageSmoothingEnabled = true;
                        hdCtx.imageSmoothingQuality = 'high';
                        hdCtx.drawImage(canvas, 0, 0, canvas.width, canvas.height, 0, 0, hdCanvas.width, hdCanvas.height);
                        // Lossless PNG (no JPEG compression noise)
                        if (hdCanvas.toBlob) {
                            hdCanvas.toBlob(function (blob) { resolve(blob); }, 'image/png');
                        } else {
                            const dataUrl = hdCanvas.toDataURL('image/png');
                            fetch(dataUrl).then(function (r) { return r.blob(); }).then(resolve).catch(function () { resolve(null); });
                        }
                    });
                });
            });
        }

        // ======================== TELEGRAM ========================
        function getTelegramConfig() { const token = (document.getElementById('botTokenInput').value || '').trim();
            const chatId = (document.getElementById('chatIdInput').value || '').trim();
            const autoSend = document.getElementById('autoTelegramToggle').classList.contains('active');
            return { token, chatId, autoSend }; }

        function setTgStatus(msg, level) { const el = document.getElementById('tgStatus'); if (!el) return;
            el.className = 'tg-status ' + (level || '');
            el.innerText = msg; if (msg) setTimeout(() => { if (el.innerText === msg) el.innerText = ''; }, 8000); }

        async function sendPhotoToTelegramWithRetry(blob, caption, maxAttempts = 3) { const { token, chatId } =
                getTelegramConfig(); if (!token || !chatId) { setTgStatus('⚠ Bot Token & Chat ID required', 'error'); return false; }
            let attempt = 0,
                lastError = null; while (attempt < maxAttempts) { attempt++;
                setTgStatus(`📡 Sending... (${attempt}/${maxAttempts})`, 'sending'); try { const formData = new FormData();
                    formData.append('chat_id', chatId);
                    formData.append('photo', blob, 'chart.png');
                    formData.append('caption', caption);
                    formData.append('parse_mode', 'HTML');
                    const url = `https://api.telegram.org/bot${token}/sendPhoto`;
                    const resp = await fetch(url, { method: 'POST', body: formData });
                    const json = await resp.json(); if (json.ok) { setTgStatus('✅ Sent to Telegram!', 'success'); return true; }
                    else { lastError = json.description || 'Send failed';
                        setTgStatus(`❌ Attempt ${attempt}: ${lastError}`, 'error'); if (attempt < maxAttempts) await new Promise(
                            r => setTimeout(r, Math.min(1500 * Math.pow(2, attempt - 1), 8000))); } } catch (err) { lastError =
                            err.message || 'Network error';
                        setTgStatus(`❌ Attempt ${attempt}: ${lastError}`, 'error'); if (attempt < maxAttempts) await new Promise(
                            r => setTimeout(r, Math.min(1500 * Math.pow(2, attempt - 1), 8000))); } }
            setTgStatus(`❌ Failed after ${maxAttempts} attempts: ${lastError}`, 'error'); return false; }

        async function sendTelegramWithRetry(blob, caption) { return await sendPhotoToTelegramWithRetry(blob, caption, 3); }

        // ======================== MESSAGE BUILDERS ========================
        function toMonospace(str) { return [...str].map(ch => { const code = ch.codePointAt(0); if (code >= 65 && code <=
                    90) return String.fromCodePoint(0x1D670 + (code - 65)); if (code >= 97 && code <= 122) return String
                    .fromCodePoint(0x1D68A + (code - 97)); if (code >= 48 && code <= 57) return String.fromCodePoint(
                    0x1D7F6 + (code - 48)); return ch; }).join(''); }

        function toBold(str) { return [...str].map(ch => { const code = ch.codePointAt(0); if (code >= 65 && code <= 90)
                    return String.fromCodePoint(0x1D5D4 + (code - 65)); if (code >= 97 && code <= 122) return String
                    .fromCodePoint(0x1D5EE + (code - 97)); if (code >= 48 && code <= 57) return String.fromCodePoint(
                    0x1D7EC + (code - 48)); return ch; }).join(''); }

        function fmtPairMono(pair) { return [...String(pair)].map(ch => { if (ch === '-') return '⁻'; return toMonospace(
                    ch); }).join(''); }

        function fmtDateMono(dateStr) { return [...String(dateStr)].map(ch => { if (ch === '.') return '．'; return toMonospace(
                    ch); }).join(''); }

        function getSignalHeader() { const raw = (document.getElementById('signalNameInput').value || '').trim() ||
                'RAVITH AI PRO';
            const hasFancy = [...raw].some(ch => ch.codePointAt(0) > 0x2000); if (hasFancy) return raw; return '👑 ' +
                toBold(raw.toUpperCase()); }

        function buildTelegramSignal(pair, timeHHMM, direction, price, payout, mtgTag) { const mPair = fmtPairMono(pair);
            const mTime = toMonospace(timeHHMM);
            const mDir = toMonospace(direction);
            const mPrice = toMonospace(String(price));
            const mPayout = toMonospace(String(payout));
            const mHeader = getSignalHeader();
            const mtgLine = mtgTag ? `\n⚙️ »» ${toMonospace(mtgTag)}` : '';
            const dirEmoji = (direction === 'BUY' || direction === 'CALL') ? '🟢' : '🔴';
            return (
                `╔═★═════════════════★═╗\n   ${mHeader}\n╚═★═════════════════★═╝\n\n╭━━━━━━━【⛨】━━━━━━━╮\n💎 »» ${mPair}\n⏰ »» ${mTime}\n${dirEmoji} »» ${mDir}\n💰 »» ${mPrice}\n💸 »» ${mPayout}٪${mtgLine}\n╰━━━━━━━━━━━━━━━━━━╯\n\n🔗 ${toMonospace('CREATE ACCOUNT')}\n🚀 ${toMonospace('BOT OWNER')}\n\n▰▰▰▰▰【 ${mHeader} 】▰▰▰▰▰`
            );
        }

        function buildTelegramResult(pair, timeHHMM, outcome, wins, losses, telegram) { const total = wins + losses;
            const rate = total ? Math.round(wins / total * 100) : 0;
            const mPair = fmtPairMono(pair);
            const mTime = toMonospace(timeHHMM);
            const mWins = toMonospace(String(wins));
            const mLosses = toMonospace(String(losses));
            const mRate = toMonospace(String(rate));
            const mHeader = getSignalHeader();
            const mTelegram = toMonospace(telegram || '@Mahabub_iX');
            const outcomeBlock = outcome === 'WIN' ?
                `        ✅✅✅ ${toMonospace('SURE SHOT')} ✅✅✅` :
                `        ❌❌❌ ${toMonospace('LOSS')} ❌❌❌`;
            return (
                `▰▱▰▱ ${toMonospace('R E S U L T')} ▰▱▰▱\n\n╭━━━━━━━【⛨】━━━━━━━╮\n🎃 ${mPair}  ┃  🕐 ${mTime}\n╰━━━━━━━━━━━━━━━━━━╯\n\n${outcomeBlock}\n\n╭━━━━━━━【⛨】━━━━━━━╮\n🔥 ${toMonospace('WIN')} ${mWins} │ ☃️ ${toMonospace('LOSS')} ${mLosses} │ (${mRate}٪)\n⚖️ ${toMonospace('PAIR')} ${mWins}×${mLosses} (${mRate}٪)\n╰━━━━━━━━━━━━━━━━━━╯\n\n🌐 ${toMonospace('TELEGRAM')} ${mTelegram}\n\n╔═★═════════════════★═╗\n      ${mHeader}\n╚═★═════════════════★═╝`
            );
        }

        function buildSignalCardText(pair, timeHHMM, direction, price, payout, mtgTag) { const dirEmoji = direction ===
                "BUY" ? "🟢" : "🔴";
            const mtgLine = mtgTag ? `\n⚙️ »» ${toMonospace(mtgTag)}` : "";
            const header = getSignalHeader();
            const mPair = fmtPairMono(pair);
            return (
                `╔═★═════════════════★═╗\n   ${header}\n╚═★═════════════════★═╝\n\n╭━━━━━━━【⛨】━━━━━━━╮\n💎 »» ${mPair}\n⏰ »» ${toMonospace(timeHHMM)}\n${dirEmoji} »» ${toMonospace(direction)}\n💰 »» ${toMonospace(String(price))}\n💸 »» ${toMonospace(String(payout))}٪${mtgLine}\n╰━━━━━━━━━━━━━━━━━━╯\n\n🔗 ${toMonospace('CREATE ACCOUNT')}\n🚀 ${toMonospace('BOT OWNER')}\n\n▰▰▰▰▰【 ${header} 】▰▰▰▰▰`
            );
        }

        function buildResultCardText(pair, timeHHMM, outcome, wins, losses, telegram) { const total = wins + losses;
            const rate = total ? Math.round(wins / total * 100) : 0;
            const header = getSignalHeader();
            const mPair = fmtPairMono(pair);
            const mWins = toMonospace(String(wins));
            const mLosses = toMonospace(String(losses));
            const mRate = toMonospace(String(rate));
            const mTelegram = toMonospace(telegram || '@Mahabub_iX');
            const outcomeBlock = outcome === 'WIN' ?
                `        ✅✅✅ ${toMonospace('SURE SHOT')} ✅✅✅` :
                `        ❌❌❌ ${toMonospace('LOSS')} ❌❌❌`;
            return (
                `▰▱▰▱ ${toMonospace('R E S U L T')} ▰▱▰▱\n\n╭━━━━━━━【⛨】━━━━━━━╮\n🎃 ${mPair}  ┃  🕐 ${toMonospace(timeHHMM)}\n╰━━━━━━━━━━━━━━━━━━╯\n\n${outcomeBlock}\n\n╭━━━━━━━【⛨】━━━━━━━╮\n🔥 ${toMonospace('WIN')} ${mWins} │ ☃️ ${toMonospace('LOSS')} ${mLosses} │ (${mRate}٪)\n⚖️ ${toMonospace('PAIR')} ${mWins}×${mLosses} (${mRate}٪)\n╰━━━━━━━━━━━━━━━━━━╯\n\n🌐 ${toMonospace('TELEGRAM')} ${mTelegram}\n\n╔═★═════════════════★═╗\n      ${header}\n╚═★═════════════════★═╝`
            );
        }

        // ======================== PARTIAL RESULT ========================
        function buildPartialResultMessage() {
            if (tradeHistory.length === 0) return "📊 No trades recorded yet.";
            const now = new Date();
            const day = String(now.getDate()).padStart(2, '0');
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const year = now.getFullYear();
            const dateStr = fmtDateMono(`${day}.${month}.${year}`);
            const otcTrades = tradeHistory.filter(t => (t.pair || '').toUpperCase().includes('OTC'));
            const realTrades = tradeHistory.filter(t => !(t.pair || '').toUpperCase().includes('OTC'));
            let lines = [];
            lines.push(`========= ${toMonospace('PARTIAL RESULTS')} ==========`);
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            lines.push(`                  📆 — ${dateStr}`);
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            lines.push(`                  📈 ${toMonospace('REAL MARKET')}`);
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            let wins = 0,
                losses = 0,
                total = 0;
            const pushTrade = (trade) => {
                const timeStr = trade.time && trade.time.length >= 16 ? trade.time.substring(11, 16) : '--:--';
                const pairDisplay = fmtPairMono(trade.pair || '??');
                const dirDisplay = toMonospace(trade.direction === 'BUY' ? 'BUY' : 'PUT');
                let outcomeSymbol = '';
                if (trade.outcome === 'win') { outcomeSymbol = '✅';
                    wins++; } else if (trade.outcome === 'mtg-win') { outcomeSymbol = '✅¹';
                    wins++; } else if (trade.outcome === 'loss') { outcomeSymbol = '✖️';
                    losses++; }
                total++;
                lines.push(`⧉ ${toMonospace(timeStr)} - ${pairDisplay} - ${dirDisplay} ${outcomeSymbol}`);
            };
            if (realTrades.length === 0) { lines.push(`——— ${toMonospace('NO REAL SIGNALS PLACED')} ———`); } else { realTrades
                    .forEach(pushTrade); }
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            lines.push(`                  📉 ${toMonospace('OTC MARKET')}`);
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            if (otcTrades.length === 0) { lines.push(`——— ${toMonospace('NO OTC SIGNALS PLACED')} ———`); } else { otcTrades
                    .forEach(pushTrade); }
            const rate = total ? Math.round((wins / total) * 100) : 0;
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            lines.push(` 🧮 ${toMonospace('PLACER')} : ${toMonospace(String(total))} 𝘅 𝟸 ◈ (${toMonospace(String(rate))}٪)`);
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            lines.push(
                ` 🚀 ${toMonospace('WIN')} : ${toMonospace(String(wins))} ┃ ${toMonospace('LOSS')} : ${toMonospace(String(losses))} ┃ ◈ (${toMonospace(String(rate))}٪)`
                );
            lines.push(`━━━━━━━━━・━━━━━━━━━`);
            return lines.join('\n');
        }

        function sendPartialResult() { const msg = buildPartialResultMessage(); if (!msg || msg ===
                "📊 No trades recorded yet.") { setTgStatus('⚠ No trades to report', 'error'); return; }
            const tgConfig = getTelegramConfig(); if (tgConfig.autoSend && tgConfig.token && tgConfig.chatId) {
                setTgStatus('📤 Sending partial results...', 'sending');
                const url = `https://api.telegram.org/bot${tgConfig.token}/sendMessage`;
                fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ chat_id: tgConfig
                            .chatId, text: msg, parse_mode: 'HTML' }) }).then(res => res.json()).then(json => { if (json
                        .ok) setTgStatus('✅ Partial results sent!', 'success'); else setTgStatus(
                        '❌ Telegram error: ' + (json.description || 'unknown'), 'error'); }).catch(err =>
                    setTgStatus('❌ Failed to send: ' + err.message, 'error')); } else { const card = document
                    .getElementById('resultCard');
                card.innerText = msg;
                card.className = 'result-card show';
                card.style.borderColor = 'rgba(139,92,246,0.5)';
                card.style.background = 'rgba(139,92,246,0.08)'; } }

        // ======================== ENGINE ========================
        const engine = { state: 'idle', currentSignal: null, initialDirection: null, initialTargetTime: null,
            signalPair: null, signalPairApi: null, mtgLevel: 0, mtgMax: 0, stats: { wins: 0, losses: 0, streakW: 0,
                streakL: 0 }, mtgWinCount: 0, mtgLossCount: 0 };
        let tradeHistory = [];
        let autoModeActive = false;
        let autoModeTimer = null;

        function getMtgMax() { const v = document.getElementById('val-martingale').innerText.trim(); if (v === 'MTG1')
                return 1; if (v === 'MTG2') return 2; if (v === 'MTG3') return 3; return 0; }

        function getTelegram() { const input = document.getElementById('telegramInput'); return input ? input.value.trim() ||
                '@Mahabub_iX' : '@Mahabub_iX'; }

        function getSelectedStrategy() { return document.getElementById('val-strategy').innerText.trim(); }

        function getSignalMode() { return document.getElementById('val-signalMode').innerText.trim(); }

        function setActionBtn(state) {
            const btn = document.getElementById('actionBtn');
            btn.classList.remove('waiting', 'mtg', 'analyzing', 'scanning', 'auto-active', 'no-credit');
            switch (state) {
                case 'analyzing':
                    btn.innerText = 'ANALYZING...';
                    btn.classList.add('analyzing');
                    break;
                case 'waiting':
                    btn.innerText = 'WAITING RESULT';
                    btn.classList.add('waiting');
                    break;
                case 'mtg':
                    btn.innerText = 'MTG WAITING';
                    btn.classList.add('mtg');
                    break;
                case 'scanning':
                    btn.innerText = 'STOP AUTO';
                    btn.classList.add('auto-active');
                    break;
                case 'no-credit':
                    btn.innerText = 'NO CREDITS LEFT';
                    btn.classList.add('no-credit');
                    break;
                default:
                    if (!hasCredits()) { btn.innerText = 'NO CREDITS LEFT';
                        btn.classList.add('no-credit'); } else btn.innerText = getSignalMode() === 'Auto' ?
                        'START AUTO' : 'GENERATE SIGNAL';
            }
        }

        function updateStatsUI() {
            document.getElementById('statWin').innerText = engine.stats.wins;
            document.getElementById('statLoss').innerText = engine.stats.losses;
            const total = engine.stats.wins + engine.stats.losses;
            const rate = total ? Math.round(engine.stats.wins / total * 100) + '%' : '--%';
            document.getElementById('statRate').innerText = rate;
            const prof = document.getElementById('profSignals');
            if (prof) prof.innerText = total;
            const profRate = document.getElementById('profRate');
            if (profRate) profRate.innerText = rate;
            saveSettings();
        }

        function showSignalCard(pair, targetTime, direction, price, payout, mtgTag) { const displayTime = engine
                .initialTargetTime || targetTime;
            const hhmm = displayTime.length >= 16 ? displayTime.substring(11, 16) : displayTime;
            const cardEl = document.getElementById('signalCard');
            cardEl.innerText = buildSignalCardText(pair, hhmm, direction, price, payout, mtgTag);
            cardEl.classList.add('show');
            document.getElementById('resultCard').classList.remove('show'); }

        function showResultCard(pair, targetTime, outcome, wins, losses) { const displayTime = engine.initialTargetTime ||
                targetTime;
            const hhmm = displayTime.length >= 16 ? displayTime.substring(11, 16) : displayTime;
            const cardEl = document.getElementById('resultCard');
            cardEl.innerText = buildResultCardText(pair, hhmm, outcome, wins, losses, getTelegram());
            cardEl.className = 'result-card show ' + (outcome === 'WIN' ? 'win' : 'loss');
            document.getElementById('signalCard').classList.remove('show'); }

        function hideSignalCard() { document.getElementById('signalCard').classList.remove('show');
            document.getElementById('resultCard').classList.remove('show'); }

        function setAutoStatusBar(msg, show, type = '') { const bar = document.getElementById('autoStatusBar');
            const txt = document.getElementById('autoStatusText'); if (show) { txt.innerText = msg;
                txt.className = type || 'scanning-text';
                bar.classList.add('show'); } else { bar.classList.remove('show'); } }

        // ======================== ADVANCED AI STRATEGY (PYTHON BOT LOGIC) ========================

        /**
         * Full Python bot strategy implementation:
         * - REVERSE: RSI divergence, overbought/oversold, reversal patterns
         * - TRENDY: Trend continuation when no strong reversal
         * - PULLBACK: Strong trend + pullback to support/resistance
         * 
         * Returns: { direction, confidence, strategy, type }
         */
        function analyzeAdvancedAI(candlesArr) {
            if (!candlesArr || candlesArr.length < 20) return null;

            const lookback = 20;
            const currentIndex = candlesArr.length - 1;
            const data = candlesArr;

            // --- Helper: RSI ---
            function calcRSI(closes, period = 14) {
                if (closes.length < period + 1) return null;
                const changes = [];
                for (let i = 1; i < closes.length; i++) changes.push(closes[i] - closes[i - 1]);
                const gains = changes.map(c => c > 0 ? c : 0);
                const losses = changes.map(c => c < 0 ? Math.abs(c) : 0);
                let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
                let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
                if (avgLoss === 0) return 100;
                let rs = avgGain / avgLoss;
                let rsi = 100 - (100 / (1 + rs));
                for (let i = period; i < changes.length; i++) {
                    avgGain = (avgGain * (period - 1) + gains[i]) / period;
                    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
                    if (avgLoss === 0) return 100;
                    rs = avgGain / avgLoss;
                    rsi = 100 - (100 / (1 + rs));
                }
                return rsi;
            }

            // --- Helper: RSI Divergence ---
            function checkDivergence(data, idx, lookback = 5) {
                if (idx < lookback + 14) return "NO_DIVERGENCE";
                const closes = data.slice(idx - lookback, idx + 1).map(c => c.close);
                const rsiValues = [];
                for (let i = idx - lookback; i <= idx; i++) {
                    const slice = data.slice(0, i + 1);
                    const r = calcRSI(slice.map(c => c.close), 14);
                    if (r !== null) rsiValues.push(r);
                    else return "NO_DIVERGENCE";
                }
                if (rsiValues.length < lookback + 1) return "NO_DIVERGENCE";

                const recentHigh = Math.max(...closes);
                const recentLow = Math.min(...closes);
                let highIdx = closes.indexOf(recentHigh);
                let lowIdx = closes.indexOf(recentLow);

                if (highIdx === -1 || lowIdx === -1) return "NO_DIVERGENCE";

                // Bearish: price higher high, RSI lower high
                if (closes[closes.length - 1] > recentHigh * 1.0001) {
                    if (rsiValues[rsiValues.length - 1] < rsiValues[highIdx]) return "BEARISH_DIVERGENCE";
                }
                // Bullish: price lower low, RSI higher low
                if (closes[closes.length - 1] < recentLow * 0.9999) {
                    if (rsiValues[rsiValues.length - 1] > rsiValues[lowIdx]) return "BULLISH_DIVERGENCE";
                }
                return "NO_DIVERGENCE";
            }

            // --- Helper: Trend Strength ---
            function calcTrend(data, idx) {
                if (idx < 5) return { strength: 0, direction: "SIDEWAYS" };
                const changes = [];
                for (let i = idx - 4; i <= idx; i++) {
                    if (i > 0) {
                        const prev = data[i - 1].close;
                        const curr = data[i].close;
                        if (prev > 0) changes.push((curr - prev) / prev * 100);
                    }
                }
                if (!changes.length) return { strength: 0, direction: "SIDEWAYS" };
                const avg = changes.reduce((a, b) => a + b, 0) / changes.length;
                const variance = changes.reduce((a, b) => a + (b - avg) ** 2, 0) / changes.length;
                const vol = Math.sqrt(variance) || 0.001;
                const strength = Math.min(Math.abs(avg) / (vol + 0.001) * 10, 100);
                let dir = "SIDEWAYS";
                if (avg > 0.01) dir = "UPTREND";
                else if (avg < -0.01) dir = "DOWNTREND";
                return { strength, direction: dir };
            }

            // --- Helper: Reversal Probability ---
            function calcReversalProb(data, idx) {
                if (idx < 3) return { prob: 0, type: "NO_REVERSAL" };
                const c = data[idx];
                const p1 = data[idx - 1];
                const p2 = data[idx - 2];
                const p3 = data[idx - 3];

                let factors = 0,
                    maxFactors = 8;

                // 1. Engulfing
                const p1Body = Math.abs(p1.close - p1.open);
                const cBody = Math.abs(c.close - c.open);
                if (p1Body > 0 && cBody > p1Body * 0.7) {
                    if ((p1.close > p1.open && c.close < c.open) || (p1.close < p1.open && c.close > c.open)) factors++;
                }

                // 2. Wick
                const totalRange = c.high - c.low;
                if (totalRange > 0) {
                    const upperWick = c.high - Math.max(c.open, c.close);
                    const lowerWick = Math.min(c.open, c.close) - c.low;
                    if ((c.close > c.open && lowerWick > cBody * 2) ||
                        (c.close < c.open && upperWick > cBody * 2)) factors++;
                    else if (upperWick > totalRange * 0.3 || lowerWick > totalRange * 0.3) factors += 0.5;
                }

                // 3. Volume spike
                if (c.volume && p1.volume && c.volume > p1.volume * 1.5) factors++;

                // 4. Close outside recent range
                const recentHigh = Math.max(p1.high, p2.high, p3.high);
                const recentLow = Math.min(p1.low, p2.low, p3.low);
                if (c.close > recentHigh || c.close < recentLow) factors++;

                // 5. Consecutive moves
                let consecutive = 0;
                for (let i = 1; i <= 3; i++) {
                    if (idx - i >= 0) {
                        const change = (data[idx - i + 1].close - data[idx - i].close) / data[idx - i].close * 100;
                        if (Math.abs(change) > 0.05) consecutive++;
                    }
                }
                if (consecutive >= 2) factors++;

                // 6. RSI overbought/oversold
                const rsi = calcRSI(data.slice(0, idx + 1).map(c => c.close), 14);
                if (rsi !== null) {
                    if (rsi >= 70 && c.close < p1.close) factors++;
                    if (rsi <= 30 && c.close > p1.close) factors++;
                }

                // 7. Dynamic SNR touch (simplified)
                const recent = data.slice(Math.max(0, idx - 15), idx);
                const sup = Math.min(...recent.map(c => c.low));
                const res = Math.max(...recent.map(c => c.high));
                if (Math.abs(c.low - sup) / sup < 0.005 && c.close > c.open) factors++;
                if (Math.abs(c.high - res) / res < 0.005 && c.close < c.open) factors++;

                const prob = Math.min((factors / maxFactors) * 100, 100);
                let type = "NO_REVERSAL";
                if (prob >= 70) type = "HIGH_REVERSAL";
                else if (prob >= 50) type = "MEDIUM_REVERSAL";
                return { prob, type };
            }

            // --- Main analysis ---
            const last = data[currentIndex];
            const trend = calcTrend(data, currentIndex);
            const rev = calcReversalProb(data, currentIndex);
            const divergence = checkDivergence(data, currentIndex);
            const rsi = calcRSI(data.slice(0, currentIndex + 1).map(c => c.close), 14);

            // --- PULLBACK Strategy ---
            if (trend.strength > 60) {
                const recent = data.slice(Math.max(0, currentIndex - 15), currentIndex);
                const sup = Math.min(...recent.map(c => c.low));
                const res = Math.max(...recent.map(c => c.high));
                if (trend.direction === "UPTREND" && Math.abs(last.close - sup) / sup < 0.005) {
                    return { direction: "BUY", confidence: 90, strategy: "PULLBACK", type: "BUY_PULLBACK_SUPPORT" };
                }
                if (trend.direction === "DOWNTREND" && Math.abs(last.close - res) / res < 0.005) {
                    return { direction: "SELL", confidence: 90, strategy: "PULLBACK", type: "SELL_PULLBACK_RESISTANCE" };
                }
            }

            // --- REVERSE Strategy (Divergence) ---
            if (divergence !== "NO_DIVERGENCE") {
                if ((divergence === "BEARISH_DIVERGENCE" && trend.direction === "UPTREND") ||
                    (divergence === "BULLISH_DIVERGENCE" && trend.direction === "DOWNTREND")) {
                    const dir = divergence === "BEARISH_DIVERGENCE" ? "SELL" : "BUY";
                    return { direction: dir, confidence: 85, strategy: "REVERSE", type: divergence };
                }
            }

            // --- REVERSE Strategy (High reversal probability) ---
            if (rev.prob >= 70 && trend.strength > 50) {
                const dir = rev.type === "HIGH_REVERSAL" ?
                    (trend.direction === "UPTREND" ? "SELL" : "BUY") :
                    (trend.direction === "UPTREND" ? "SELL" : "BUY");
                return { direction: dir, confidence: rev.prob, strategy: "REVERSE", type: rev.type };
            }

            // --- REVERSE Strategy (RSI overbought/oversold) ---
            if (rsi !== null) {
                if (rsi >= 70 && trend.direction === "UPTREND") {
                    return { direction: "SELL", confidence: Math.min(rev.prob * 0.5 + 60, 100), strategy: "REVERSE",
                        type: "RSI_OVEREXTENDED" };
                }
                if (rsi <= 30 && trend.direction === "DOWNTREND") {
                    return { direction: "BUY", confidence: Math.min(rev.prob * 0.5 + 60, 100), strategy: "REVERSE",
                        type: "RSI_OVEREXTENDED" };
                }
            }

            // --- SNR REVERSE (simplified) ---
            const recent2 = data.slice(Math.max(0, currentIndex - 15), currentIndex);
            const sup2 = Math.min(...recent2.map(c => c.low));
            const res2 = Math.max(...recent2.map(c => c.high));
            if (trend.direction === "UPTREND" && Math.abs(last.close - res2) / res2 < 0.005) {
                return { direction: "SELL", confidence: 75, strategy: "REVERSE", type: "SNR_REJECTION" };
            }
            if (trend.direction === "DOWNTREND" && Math.abs(last.close - sup2) / sup2 < 0.005) {
                return { direction: "BUY", confidence: 75, strategy: "REVERSE", type: "SNR_REJECTION" };
            }

            // --- TRENDY Strategy (default) ---
            if (rev.prob <= 30 && trend.strength > 40) {
                const dir = trend.direction === "UPTREND" ? "BUY" : (trend.direction === "DOWNTREND" ? "SELL" : "BUY");
                return { direction: dir, confidence: trend.strength, strategy: "TRENDY", type: "TREND_CONTINUATION" };
            }

            // --- Fallback: Mixed conditions ---
            const fallbackDir = trend.direction === "UPTREND" ? "BUY" : (trend.direction === "DOWNTREND" ? "SELL" : "BUY");
            return { direction: fallbackDir, confidence: Math.max(trend.strength, 100 - rev.prob), strategy: "TRENDY",
                type: "MIXED_CONDITIONS" };
        }

        // ======================== SUPPORT/RESISTANCE TOUCH STRATEGY (body/wick) ========================

        /**
         * Support/Resistance Touch:
         * Detects if the latest candle's body (open-close) or wick (high-low) touches a support or resistance level.
         * - Resistance touch: high >= resistance and low <= resistance (candle range covers the level)
         * - Support touch: high >= support and low <= support
         * Then generate SELL at resistance, BUY at support.
         */
        function analyzeSupportResistanceTouch(candlesArr) {
            if (!candlesArr || candlesArr.length < 15) return null;
            const lookback = 30;
            const recent = candlesArr.slice(-lookback);
            const last = candlesArr[candlesArr.length - 1];
            // Find swing highs/lows for S/R
            const swingHighs = [];
            const swingLows = [];
            for (let i = 2; i < recent.length - 2; i++) {
                if (recent[i].high > recent[i - 1].high && recent[i].high > recent[i - 2].high &&
                    recent[i].high > recent[i + 1].high && recent[i].high > recent[i + 2].high) {
                    swingHighs.push(recent[i].high);
                }
                if (recent[i].low < recent[i - 1].low && recent[i].low < recent[i - 2].low &&
                    recent[i].low < recent[i + 1].low && recent[i].low < recent[i + 2].low) {
                    swingLows.push(recent[i].low);
                }
            }
            if (!swingHighs.length || !swingLows.length) return null; // need both
            const resistance = Math.max(...swingHighs);
            const support = Math.min(...swingLows);
            const range = resistance - support || 0.0001;
            const tolerance = range * 0.01; // 1% tolerance for touch

            // Check if candle's range touches resistance (high >= resistance && low <= resistance)
            const touchesResistance = (last.high >= resistance - tolerance) && (last.low <= resistance + tolerance);
            const touchesSupport = (last.high >= support - tolerance) && (last.low <= support + tolerance);

            if (touchesResistance) {
                return { direction: "SELL", confidence: 85, strategy: "SUPPORT_RESISTANCE_TOUCH",
                    type: "RESISTANCE_TOUCH" };
            } else if (touchesSupport) {
                return { direction: "BUY", confidence: 85, strategy: "SUPPORT_RESISTANCE_TOUCH",
                    type: "SUPPORT_TOUCH" };
            }
            return null;
        }

        // ======================== EMA TREND CROSS STRATEGY ========================

        /**
         * EMA Trend Cross:
         * Generates BUY when close crosses above a fast EMA (9) and above slow EMA (20) (bullish cross)
         * Generates SELL when close crosses below fast EMA and below slow EMA (bearish cross)
         * We use 9 and 20 period EMAs.
         */
        function analyzeEMATrend(candlesArr) {
            if (!candlesArr || candlesArr.length < 25) return null;
            const closes = candlesArr.map(c => c.close);
            const ema9 = calculateEMA(candlesArr, 9);
            const ema20 = calculateEMA(candlesArr, 20);
            if (ema9.length < 2 || ema20.length < 2) return null;
            const lastIdx = candlesArr.length - 1;
            const prevIdx = lastIdx - 1;
            const lastClose = candlesArr[lastIdx].close;
            const prevClose = candlesArr[prevIdx].close;
            const lastEma9 = ema9[lastIdx];
            const prevEma9 = ema9[prevIdx];
            const lastEma20 = ema20[lastIdx];
            const prevEma20 = ema20[prevIdx];

            // Bullish cross: close crosses above both EMAs, and previous close was below or equal
            if (lastClose > lastEma9 && lastClose > lastEma20 && (prevClose <= prevEma9 || prevClose <= prevEma20)) {
                return { direction: "BUY", confidence: 78, strategy: "EMA_TREND", type: "BULLISH_CROSS" };
            }
            // Bearish cross: close crosses below both EMAs, and previous close was above or equal
            if (lastClose < lastEma9 && lastClose < lastEma20 && (prevClose >= prevEma9 || prevClose >= prevEma20)) {
                return { direction: "SELL", confidence: 78, strategy: "EMA_TREND", type: "BEARISH_CROSS" };
            }
            return null;
        }

        // ======================== RSI REVERSAL STRATEGY ========================

        /**
         * RSI Reversal:
         * Combines RSI overbought/oversold with price touching support/resistance.
         * - SELL when RSI >= 70 and price touches resistance (candle range covers resistance)
         * - BUY when RSI <= 30 and price touches support
         */
        function analyzeRSIReversal(candlesArr) {
            if (!candlesArr || candlesArr.length < 20) return null;
            const last = candlesArr[candlesArr.length - 1];
            // Calculate RSI
            const closes = candlesArr.map(c => c.close);
            let rsi = null;
            // Simple RSI calculation (using the same function from AI)
            function calcRSI_simple(closes, period = 14) {
                if (closes.length < period + 1) return null;
                const changes = [];
                for (let i = 1; i < closes.length; i++) changes.push(closes[i] - closes[i - 1]);
                const gains = changes.map(c => c > 0 ? c : 0);
                const losses = changes.map(c => c < 0 ? Math.abs(c) : 0);
                let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
                let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
                if (avgLoss === 0) return 100;
                let rs = avgGain / avgLoss;
                let rsi_val = 100 - (100 / (1 + rs));
                for (let i = period; i < changes.length; i++) {
                    avgGain = (avgGain * (period - 1) + gains[i]) / period;
                    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
                    if (avgLoss === 0) return 100;
                    rs = avgGain / avgLoss;
                    rsi_val = 100 - (100 / (1 + rs));
                }
                return rsi_val;
            }
            rsi = calcRSI_simple(closes, 14);
            if (rsi === null) return null;

            // Determine S/R levels
            const lookback = 30;
            const recent = candlesArr.slice(-lookback);
            const swingHighs = [];
            const swingLows = [];
            for (let i = 2; i < recent.length - 2; i++) {
                if (recent[i].high > recent[i - 1].high && recent[i].high > recent[i - 2].high &&
                    recent[i].high > recent[i + 1].high && recent[i].high > recent[i + 2].high) {
                    swingHighs.push(recent[i].high);
                }
                if (recent[i].low < recent[i - 1].low && recent[i].low < recent[i - 2].low &&
                    recent[i].low < recent[i + 1].low && recent[i].low < recent[i + 2].low) {
                    swingLows.push(recent[i].low);
                }
            }
            if (!swingHighs.length || !swingLows.length) return null;
            const resistance = Math.max(...swingHighs);
            const support = Math.min(...swingLows);
            const range = resistance - support || 0.0001;
            const tolerance = range * 0.01;

            const touchesResistance = (last.high >= resistance - tolerance) && (last.low <= resistance + tolerance);
            const touchesSupport = (last.high >= support - tolerance) && (last.low <= support + tolerance);

            // RSI overbought (>= 70) and touches resistance -> SELL
            if (rsi >= 70 && touchesResistance) {
                return { direction: "SELL", confidence: 82, strategy: "RSI_REVERSAL", type: "RSI_OVERBOUGHT_RESISTANCE" };
            }
            // RSI oversold (<= 30) and touches support -> BUY
            if (rsi <= 30 && touchesSupport) {
                return { direction: "BUY", confidence: 82, strategy: "RSI_REVERSAL", type: "RSI_OVERSOLD_SUPPORT" };
            }
            return null;
        }

        // ======================== STRATEGY DISPATCH ========================


        function analyzeBollinger(candlesArr) {
            if (!candlesArr || candlesArr.length < 22) return null;
            const period = 20, mult = 2;
            const closes = candlesArr.map(c => c.close);
            const slice = closes.slice(-period);
            const mean = slice.reduce((a,b)=>a+b,0) / period;
            const variance = slice.reduce((a,b)=>a+(b-mean)*(b-mean),0) / period;
            const std = Math.sqrt(variance) || 0.0001;
            const upper = mean + mult * std, lower = mean - mult * std;
            const last = candlesArr[candlesArr.length - 1];
            const prev = candlesArr[candlesArr.length - 2];
            if (prev.close >= lower && last.close < lower && last.close < last.open)
                return { direction: 'BUY', confidence: 80, strategy: 'BOLLINGER', type: 'LOWER_BAND_BOUNCE' };
            if (prev.close <= upper && last.close > upper && last.close > last.open)
                return { direction: 'SELL', confidence: 80, strategy: 'BOLLINGER', type: 'UPPER_BAND_REJECT' };
            return null;
        }

        function analyzeMACD(candlesArr) {
            if (!candlesArr || candlesArr.length < 35) return null;
            function emaArr(data, p) {
                const k = 2/(p+1); let e = data[0]; const out=[e];
                for (let i=1;i<data.length;i++){ e = data[i]*k + e*(1-k); out.push(e); }
                return out;
            }
            const closes = candlesArr.map(c => c.close);
            const ema12 = emaArr(closes, 12), ema26 = emaArr(closes, 26);
            const macd = ema12.map((v,i)=>v - ema26[i]);
            const signal = emaArr(macd, 9);
            const i = macd.length - 1;
            if (i < 1) return null;
            if (macd[i-1] <= signal[i-1] && macd[i] > signal[i])
                return { direction: 'BUY', confidence: 78, strategy: 'MACD', type: 'BULLISH_CROSS' };
            if (macd[i-1] >= signal[i-1] && macd[i] < signal[i])
                return { direction: 'SELL', confidence: 78, strategy: 'MACD', type: 'BEARISH_CROSS' };
            return null;
        }

        function analyzeStochastic(candlesArr) {
            if (!candlesArr || candlesArr.length < 16) return null;
            const period = 14;
            const slice = candlesArr.slice(-period);
            const last = candlesArr[candlesArr.length - 1];
            const hi = Math.max(...slice.map(c=>c.high));
            const lo = Math.min(...slice.map(c=>c.low));
            const range = hi - lo || 0.0001;
            const k = ((last.close - lo) / range) * 100;
            if (k <= 20 && last.close > last.open)
                return { direction: 'BUY', confidence: 81, strategy: 'STOCHASTIC', type: 'OVERSOLD_REVERSAL' };
            if (k >= 80 && last.close < last.open)
                return { direction: 'SELL', confidence: 81, strategy: 'STOCHASTIC', type: 'OVERBOUGHT_REVERSAL' };
            return null;
        }

        function analyzeTrendPullback(candlesArr) {
            if (!candlesArr || candlesArr.length < 25) return null;
            const ema9 = calculateEMA(candlesArr, 9);
            const ema21 = calculateEMA(candlesArr, 21);
            const i = candlesArr.length - 1;
            const last = candlesArr[i];
            if (ema9[i] > ema21[i] && last.low <= ema21[i] && last.close > ema21[i] && last.close > last.open)
                return { direction: 'BUY', confidence: 84, strategy: 'TREND_PULLBACK', type: 'BUY_PULLBACK_EMA' };
            if (ema9[i] < ema21[i] && last.high >= ema21[i] && last.close < ema21[i] && last.close < last.open)
                return { direction: 'SELL', confidence: 84, strategy: 'TREND_PULLBACK', type: 'SELL_PULLBACK_EMA' };
            return null;
        }

        function analyzeBreakoutSpike(candlesArr) {
            if (!candlesArr || candlesArr.length < 20) return null;
            const look = candlesArr.slice(-16, -1);
            const last = candlesArr[candlesArr.length - 1];
            const res = Math.max(...look.map(c=>c.high));
            const sup = Math.min(...look.map(c=>c.low));
            const body = Math.abs(last.close - last.open);
            const avgBody = look.reduce((a,c)=>a+Math.abs(c.close-c.open),0) / look.length || 0.0001;
            if (last.close > res && body > avgBody * 1.4)
                return { direction: 'BUY', confidence: 83, strategy: 'BREAKOUT', type: 'RESISTANCE_BREAK' };
            if (last.close < sup && body > avgBody * 1.4)
                return { direction: 'SELL', confidence: 83, strategy: 'BREAKOUT', type: 'SUPPORT_BREAK' };
            return null;
        }

        async function analyzeWithStrategy(candlesArr, strategy) {
            if (!candlesArr || candlesArr.length < 10) return null;
            const last = candlesArr[candlesArr.length - 1];
            const price = last.close;
            const time = last.time || '';

            switch (strategy) {
                case 'Support/Resistance Touch':
                    const srResult = analyzeSupportResistanceTouch(candlesArr);
                    if (srResult) {
                        return { direction: srResult.direction, price: price, time: time, payout: currentPayout || 0,
                            confidence: srResult.confidence, strategy: srResult.strategy, type: srResult.type };
                    }
                    return null;
                case 'EMA Trend Cross':
                    const emaResult = analyzeEMATrend(candlesArr);
                    if (emaResult) {
                        return { direction: emaResult.direction, price: price, time: time, payout: currentPayout || 0,
                            confidence: emaResult.confidence, strategy: emaResult.strategy, type: emaResult.type };
                    }
                    return null;
                case 'RSI Reversal':
                    const rsiResult = analyzeRSIReversal(candlesArr);
                    if (rsiResult) {
                        return { direction: rsiResult.direction, price: price, time: time, payout: currentPayout || 0,
                            confidence: rsiResult.confidence, strategy: rsiResult.strategy, type: rsiResult.type };
                    }
                    return null;
                case 'Bollinger Bands': {
                    const r = analyzeBollinger(candlesArr);
                    if (r) return { direction: r.direction, price: price, time: time, payout: currentPayout || 0, confidence: r.confidence, strategy: r.strategy, type: r.type };
                    return null;
                }
                case 'MACD Momentum': {
                    const r = analyzeMACD(candlesArr);
                    if (r) return { direction: r.direction, price: price, time: time, payout: currentPayout || 0, confidence: r.confidence, strategy: r.strategy, type: r.type };
                    return null;
                }
                case 'Stochastic Reversal': {
                    const r = analyzeStochastic(candlesArr);
                    if (r) return { direction: r.direction, price: price, time: time, payout: currentPayout || 0, confidence: r.confidence, strategy: r.strategy, type: r.type };
                    return null;
                }
                case 'Trend Pullback': {
                    const r = analyzeTrendPullback(candlesArr);
                    if (r) return { direction: r.direction, price: price, time: time, payout: currentPayout || 0, confidence: r.confidence, strategy: r.strategy, type: r.type };
                    return null;
                }
                case 'Breakout Spike': {
                    const r = analyzeBreakoutSpike(candlesArr);
                    if (r) return { direction: r.direction, price: price, time: time, payout: currentPayout || 0, confidence: r.confidence, strategy: r.strategy, type: r.type };
                    return null;
                }
                case 'AI Smart Signal':
                default:
                    const aiResult = analyzeAdvancedAI(candlesArr);
                    if (aiResult && aiResult.confidence >= 60) {
                        return { direction: aiResult.direction, price: price, time: time, payout: currentPayout || 0,
                            confidence: aiResult.confidence, strategy: aiResult.strategy, type: aiResult.type };
                    }
                    return null;
            }
        }

        // ======================== SIGNAL GENERATION ========================

        async function onActionClick() {
            const mode = getSignalMode();
            if (mode === 'Auto') { if (autoModeActive) { stopAutoMode(); } else { startAutoMode(); } return; }
            if (engine.state !== 'idle') return;
            if (!hasCredits()) { showToast('No credits remaining! Wait for daily reset or upgrade to Pro.');
                setActionBtn('no-credit'); return; }
            generateManualSignal();
        }

        async function generateManualSignal() {
            engine.state = 'analyzing';
            setActionBtn('analyzing');
            hideSignalCard();
            const strategy = getSelectedStrategy();
            const signalPair = currentPair;
            const signalPairApi = currentApiPair;
            await loadData(signalPairApi);
            if (!allCandles || allCandles.length < 10) { setChartStatus("NO DATA AVAILABLE", "warn");
                engine.state = 'idle';
                setActionBtn('idle'); return; }
            const result = await analyzeWithStrategy(allCandles, strategy);
            if (!result) { setChartStatus("NO SIGNAL — " + strategy, "warn");
                engine.state = 'idle';
                setActionBtn('idle'); return; }
            const creditOk = await useOneCredit();
            if (!creditOk) { engine.state = 'idle';
                setActionBtn('no-credit'); return; }
            const direction = result.direction;
            const price = result.price;
            const payout = result.payout || currentPayout || 0;
            // ENTRY TIME = current live running candle + 1 minute.
            // Use the live candle identifier from the chart feed, not the last
            // closed candle or a server-clock calculation.
            const liveBase = (liveCandle && liveCandle.time) ? liveCandle.time : result.time;
            const targetTime = nextMinuteTime(liveBase, 1);
            engine.currentSignal = { direction, price, targetTime, payout, mtgStep: 0, entryTime: liveBase };
            engine.initialDirection = direction;
            engine.initialTargetTime = targetTime;
            engine.signalPair = signalPair;
            engine.signalPairApi = signalPairApi;
            engine.mtgLevel = 0;
            engine.mtgMax = getMtgMax();
            if (liveCandle) liveCandle.signal = direction;
            showSignalCard(signalPair, targetTime, direction, price, payout, null);
            engine.state = 'waiting';
            setActionBtn('waiting');
            requestDraw();
            sendSignalToTelegram(signalPair, targetTime, direction, price, payout, null);
            startResultPolling();
        }

        // ======================== AUTO MODE ========================

        function startAutoMode() {
            if (!hasCredits()) { showToast('No credits remaining!');
                setActionBtn('no-credit'); return; }
            autoModeActive = true;
            setActionBtn('scanning');
            setAutoStatusBar('🔄 SCANNING MARKETS...', true, 'scanning-text');
            autoScanLoop();
        }

        function stopAutoMode() { autoModeActive = false; if (autoModeTimer) { clearTimeout(autoModeTimer);
                autoModeTimer = null; } stopResultPolling();
            setAutoStatusBar('', false); if (engine.state === 'idle') setActionBtn('idle'); }

        async function autoScanLoop() {
            if (!autoModeActive) return;
            if (engine.state !== 'idle') { autoModeTimer = setTimeout(autoScanLoop, 5000); return; }
            if (!hasCredits()) { showToast('No credits remaining!');
                stopAutoMode();
                setActionBtn('no-credit'); return; }
            const strategy = getSelectedStrategy();
            const markets = selectedAutoMarkets.length ? selectedAutoMarkets : ALL_MARKETS;
            setAutoStatusBar(`🔍 SCANNING ${markets.length} MARKETS (${strategy})...`, true, 'scanning-text');
            for (let i = 0; i < markets.length; i++) {
                if (!autoModeActive) return;
                if (engine.state !== 'idle') { autoModeTimer = setTimeout(autoScanLoop, 5000); return; }
                const pair = markets[i];
                const pairApi = displayPairToApi(pair);
                setAutoStatusBar(`📊 ANALYZING ${pair} (${i + 1}/${markets.length})...`, true, 'scanning-text');
                try {
                    const url =
                        API_BASE + '/?Pair=' + encodeURIComponent(pairApi) + '&Candle=100&Time=1m';
                    const resp = await fetch(url, { cache: "no-store" });
                    const json = await resp.json();
                    if (!json || !Array.isArray(json.data) || json.data.length < 10) continue;
                    const candlesArr = json.data.map(c => ({ open: Number(c.open), high: Number(c.high), low: Number(c
                            .low), close: Number(c.close), signal: String(c.signal || '').trim().toUpperCase(),
                        payout: Number(c.payout || 0), time: c.time || '', pair: c.pair || '' })).filter(c =>
                        Number.isFinite(c.open) && Number.isFinite(c.close)).reverse();
                    if (candlesArr.length < 10) continue;
                    const result = await analyzeWithStrategy(candlesArr, strategy);
                    if (result) {
                        const last = candlesArr[candlesArr.length - 1];
                        const payoutSample = candlesArr.slice(-30).map(c => c.payout).filter(p => p > 0);
                        const payout = payoutSample.length ? Math.round(payoutSample.reduce((a, b) => a + b, 0) /
                            payoutSample.length) : 0;
                        setAutoStatusBar(`🚀 SIGNAL FOUND: ${pair} ${result.direction}`, true, 'signal-found');
                        await executeAutoSignal(pair, pairApi, result.direction, result.price || last.close, payout ||
                            currentPayout || 0, result.time || last.time);
                        return;
                    }
                } catch (e) { console.error('Auto scan error:', pair, e); }
                await new Promise(r => setTimeout(r, 200));
            }
            if (autoModeActive) { setAutoStatusBar(`⏳ NO SIGNAL — RESCANNING IN 8s...`, true, 'no-signal');
                autoModeTimer = setTimeout(autoScanLoop, 8000); }
        }

        async function executeAutoSignal(pair, pairApi, direction, price, payout, baseTime) {
            if (!autoModeActive) return;
            const creditOk = await useOneCredit();
            if (!creditOk) { stopAutoMode();
                setActionBtn('no-credit'); return; }
            if (currentPair !== pair) { currentPair = pair;
                currentApiPair = pairApi;
                document.getElementById('val-market').innerText = pair;
                await loadData(pairApi);
                startLiveTicks(); }
            // ENTRY TIME = live running candle + 1 minute, matching manual signals.
            // baseTime is supplied by the auto-scan cycle; prefer the current live
            // candle for the selected market so entry timing follows real ticks.
            const liveBaseAuto = (pairApi === currentApiPair && liveCandle && liveCandle.time)
                ? liveCandle.time
                : (baseTime || (allCandles.length ? allCandles[allCandles.length - 1].time : ''));
            const targetTime = nextMinuteTime(liveBaseAuto, 1);
            engine.currentSignal = { direction, price, targetTime, payout, mtgStep: 0, entryTime: liveBaseAuto };
            engine.initialDirection = direction;
            engine.initialTargetTime = targetTime;
            engine.signalPair = pair;
            engine.signalPairApi = pairApi;
            engine.mtgLevel = 0;
            engine.mtgMax = getMtgMax();
            if (liveCandle) liveCandle.signal = direction;
            showSignalCard(pair, targetTime, direction, price, payout, null);
            setAutoStatusBar(`📈 ${pair} ${direction} @ ${price}`, true, 'signal-found');
            engine.state = 'waiting';
            setActionBtn('scanning');
            requestDraw();
            sendSignalToTelegram(pair, targetTime, direction, price, payout, null);
            startResultPolling();
        }

        // ======================== TELEGRAM SEND ========================

        function sendSignalToTelegram(pair, targetTime, direction, price, payout, mtgTag) {
            const tgConfig = getTelegramConfig();
            if (tgConfig.autoSend && tgConfig.token && tgConfig.chatId) {
                setTimeout(async () => {
                    try {
                        const chartBlob = await getChartScreenshot();
                        const displayTime = targetTime.length >= 16 ? targetTime.substring(11, 16) : targetTime;
                        const caption = buildTelegramSignal(pair, displayTime, direction, price, payout, mtgTag);
                        await sendTelegramWithRetry(chartBlob, caption);
                    } catch (err) { console.error('Telegram signal send error:', err);
                        setTgStatus('❌ Screenshot error', 'error'); }
                }, 300);
            }
        }

        function sendResultToTelegram(pair, targetTime, outcome) {
            const tgConfig = getTelegramConfig();
            if (tgConfig.autoSend && tgConfig.token && tgConfig.chatId) {
                setTimeout(async () => {
                    try {
                        const chartBlob = await getChartScreenshot();
                        const displayTime = engine.initialTargetTime || targetTime;
                        const hhmm = displayTime && displayTime.length >= 16 ? displayTime.substring(11, 16) :
                            '00:00';
                        const caption = buildTelegramResult(pair, hhmm, outcome, engine.stats.wins, engine.stats
                            .losses, getTelegram());
                        await sendTelegramWithRetry(chartBlob, caption);
                    } catch (err) { console.error('Telegram result send error:', err); }
                }, 300);
            }
        }

        // ======================== MTG ========================

        function generateMtgSignal() {
            const pair = engine.signalPair || currentPair;
            const direction = engine.initialDirection;
            const price = engine.currentSignal ? engine.currentSignal.price : latestClosePrice;
            const payout = engine.currentSignal ? engine.currentSignal.payout : currentPayout || 0;
            const currentTarget = engine.currentSignal.targetTime;
            const nextTarget = nextMinuteTime(currentTarget, 1);
            const step = engine.mtgLevel + 1;
            engine.currentSignal = { direction: direction, price: price, targetTime: nextTarget, payout: payout,
                mtgStep: step };
            engine.mtgLevel = step;
            if (liveCandle) liveCandle.signal = direction;
            showSignalCard(pair, nextTarget, direction, price, payout, 'MTG' + step);
            engine.state = 'mtg';
            setActionBtn('mtg');
            requestDraw();
            startResultPolling();
        }

        // ======================== RESULT POLLING ========================

        let resultPoller = null;

        function startResultPolling() { stopResultPolling();
            resultPoller = setInterval(pollForTargetCandle, 5000);
            pollForTargetCandle(); }

        function stopResultPolling() { if (resultPoller) { clearInterval(resultPoller);
                resultPoller = null; } }

        async function pollForTargetCandle() { if (!engine.currentSignal) { stopResultPolling(); return; }
            const pairApi = engine.signalPairApi || currentApiPair;
            await loadData(pairApi); }

        function evaluateWaitingResult() {
            if (!engine.currentSignal) return;
            if (engine.state !== 'waiting' && engine.state !== 'mtg') return;
            const target = findCandleByTime(allCandles, engine.currentSignal.targetTime);
            if (!target) return;
            const dir = engine.currentSignal.direction;
            let outcome;
            if (target.close > target.open) outcome = (dir === 'BUY') ? 'WIN' : 'LOSS';
            else if (target.close < target.open) outcome = (dir === 'SELL') ? 'WIN' : 'LOSS';
            else outcome = 'LOSS';
            stopResultPolling();
            applyOutcome(outcome, target);
        }

        function applyOutcome(outcome) {
            const pair = engine.signalPair || currentPair;
            const targetTime = engine.currentSignal.targetTime;
            let outcomeType = '';
            let isMtg = engine.mtgLevel > 0;
            if (outcome === 'WIN') {
                engine.stats.wins++;
                engine.stats.streakW++;
                engine.stats.streakL = 0;
                outcomeType = isMtg ? 'mtg-win' : 'win';
                tradeHistory.push({ time: targetTime, pair: pair, direction: engine.initialDirection, outcome: outcomeType });
                updateStatsUI();
                showResultCard(pair, targetTime, 'WIN', engine.stats.wins, engine.stats.losses);
                if (liveCandle) liveCandle.signal = '';
                sendResultToTelegram(pair, targetTime, 'WIN');
                finalizeSession();
                return;
            }
            if (engine.mtgLevel < engine.mtgMax) { generateMtgSignal(); return; }
            engine.stats.losses++;
            engine.stats.streakL++;
            engine.stats.streakW = 0;
            outcomeType = 'loss';
            tradeHistory.push({ time: targetTime, pair: pair, direction: engine.initialDirection, outcome: outcomeType });
            updateStatsUI();
            showResultCard(pair, targetTime, 'LOSS', engine.stats.wins, engine.stats.losses);
            if (liveCandle) liveCandle.signal = '';
            sendResultToTelegram(pair, targetTime, 'LOSS');
            finalizeSession();
        }

        function finalizeSession() {
            engine.state = 'idle';
            engine.initialTargetTime = null;
            engine.signalPair = null;
            engine.signalPairApi = null;
            engine.mtgLevel = 0;
            if (autoModeActive) { setActionBtn('scanning');
                setAutoStatusBar('🔄 RESULT DONE — CONTINUING SCAN...', true, 'scanning-text');
                autoModeTimer = setTimeout(autoScanLoop, 3000); } else { setActionBtn('idle');
                setAutoStatusBar('', false); }
            requestDraw();
            saveSettings();
        }

        function resetResult() {
            stopResultPolling();
            stopAutoMode();
            engine.state = 'idle';
            engine.currentSignal = null;
            engine.initialDirection = null;
            engine.initialTargetTime = null;
            engine.signalPair = null;
            engine.signalPairApi = null;
            engine.mtgLevel = 0;
            engine.mtgMax = getMtgMax();
            engine.stats = { wins: 0, losses: 0, streakW: 0, streakL: 0 };
            tradeHistory = [];
            if (liveCandle) liveCandle.signal = '';
            setActionBtn('idle');
            hideSignalCard();
            setTgStatus('', '');
            setAutoStatusBar('', false);
            updateStatsUI();
            requestDraw();
            saveSettings();
        }

        // ======================== TIME HELPERS ========================

        function parseCandleTime(str) { if (!str) return null; const m = str.match(
                /^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/); if (!m) return null; return new Date(+m[1], +m[
                2] - 1, +m[3], +m[4], +m[5], +m[6]); }

        function formatCandleTime(date) { const p = n => n < 10 ? "0" + n : "" + n; return `${date.getFullYear()}-${p(date
                .getMonth() + 1)}-${p(date.getDate())} ${p(date.getHours())}:${p(date.getMinutes())}:00`; }

        function nextMinuteTime(str, offsetMinutes = 1) { const d = parseCandleTime(str); if (!d) return '';
            d.setSeconds(0);
            d.setMinutes(d.getMinutes() + offsetMinutes); return formatCandleTime(d); }

        function findCandleByTime(pool, timeStr) { if (!pool) return null; for (let i = pool.length - 1; i >= 0; i--) { if (
                    pool[i].time === timeStr) return pool[i]; } return null; }

        // ======================== MARKET / TIMEFRAME ========================

        async function onMarketChanged(newDisplayPair) { currentPair = newDisplayPair;
            currentApiPair = displayPairToApi(newDisplayPair);
            candles = [];
            allCandles = [];
            liveCandle = null;
            stopResultPolling();
            engine.state = 'idle';
            engine.currentSignal = null;
            engine.initialTargetTime = null;
            engine.mtgLevel = 0;
            setActionBtn('idle');
            hideSignalCard();
            setChartStatus("SWITCHING", "ok");
            requestDraw();
            await loadData(currentApiPair);
            startLiveTicks();
            saveSettings(); }

        function onTimeframeChanged(newTf) { if (newTf !== '1 Minute') { setChartStatus("1M ENGINE", "warn");
                setTimeout(() => setChartStatus("LIVE", "ok"), 1800); } saveSettings(); }

        // ======================== INIT ========================

        async function initEngine() {
            if (!isLoggedIn()) { setAuthVisibility(true); return; }
            setAuthVisibility(false);
            currentPair = document.getElementById('val-market').innerText.trim();
            currentApiPair = displayPairToApi(currentPair);

            await loadSettings();

            currentPair = document.getElementById('val-market').innerText.trim();
            currentApiPair = displayPairToApi(currentPair);

            updateStatsUI();
            updateProfileUI();
            chartResize();

            loadData(currentApiPair).then(() => { startLiveTicks(); });

            fetchUserCount();
            refreshProfile();

            const wm = document.getElementById('watermarkInput').value;
            if (wm) document.documentElement.style.setProperty('--watermark-text', '"' + wm + '"');
            const dn = document.getElementById('dashboardNameInput').value;
            if (dn) document.documentElement.style.setProperty('--dashboard-name', '"' + dn + '"');
        }

        // ======================== BOOT ========================

        if (loadSession()) { initEngine(); } else { setAuthVisibility(true); }

        setInterval(function () { if (currentApiPair) loadData(currentApiPair, true); }, 8000);
        setInterval(() => { requestDraw(); }, 1000);
        setInterval(fetchUserCount, 30000);
        setInterval(refreshProfile, 120000);

        window.addEventListener('beforeunload', () => { try { flushSettingsNow(); } catch (e) {} });
        window.addEventListener('pagehide', () => { try { flushSettingsNow(); } catch (e) {} });

        // Expose globals
        window.onActionClick = onActionClick;
        window.resetResult = resetResult;
        window.sendPartialResult = sendPartialResult;
        window.openDialog = openDialog;
        window.closeDialog = closeDialog;
        window.toggleSwitch = toggleSwitch;
        window.toggleDarkMode = toggleDarkMode;
        window.switchView = switchView;
        window.resetAll = resetAll;
        window.logoutUser = logoutUser;
        window.handleLogin = handleLogin;
        window.selectItem = selectItem;
        window.toggleAutoMarket = toggleAutoMarket;
        window.chartResize = chartResize;
        window.copyUID = copyUID;


        // ======================== FUTURE CHECKER ========================
        function fcLoadSample() {
            const el = document.getElementById('fcSignalInput');
            if (!el) return;
            const now = new Date();
            const hh = String(now.getHours()).padStart(2, '0');
            const mm = String(Math.max(0, now.getMinutes() - 5)).padStart(2, '0');
            el.value = `⧉ 𝚄𝚂𝙳𝙱𝙳𝚃-𝙾𝚃𝙲 - 𝟷𝟺⁚${mm} ⇨ 𝙱𝚄𝚈\n⧉ 𝙴𝚄𝚁𝚄𝚂𝙳-𝙾𝚃𝙲 - ${hh}:${mm} ⇨ 𝙿𝚄𝚃`;
        }

        // Normalize mathematical/stylized alphabets, digits, separators and arrows.
        function fcDefancyText(value) {
            let s = String(value || '').normalize('NFKD');
            const map = {
                '⁚': ':', '：': ':', '﹕': ':', '．': '.', '。': '.',
                '⇨': ' -> ', '➔': ' -> ', '➡': ' -> ', '→': ' -> ', '⟶': ' -> ',
                '⁻': '-', '−': '-', '—': '-', '–': '-', '﹣': '-', '＿': '_',
                '𝟎':'0','𝟏':'1','𝟐':'2','𝟑':'3','𝟒':'4','𝟓':'5','𝟔':'6','𝟕':'7','𝟖':'8','𝟗':'9',
                '𝟘':'0','𝟙':'1','𝟚':'2','𝟛':'3','𝟜':'4','𝟝':'5','𝟞':'6','𝟟':'7','𝟠':'8','𝟡':'9'
            };
            return [...s].map(ch => map[ch] !== undefined ? map[ch] : ch).join('')
                .replace(/[\u{1D400}-\u{1D7FF}]/gu, ch => {
                    const cp = ch.codePointAt(0);
                    // NFKD handles most mathematical alphabets; this covers remaining bold/mono digits.
                    if (cp >= 0x1D7CE && cp <= 0x1D7FF) return String((cp - 0x1D7CE) % 10);
                    return ch;
                });
        }

        function parseFcSignals(text) {
            const out = [];
            const seen = new Set();
            for (const raw of String(text || '').split(/\r?\n/)) {
                let line = fcDefancyText(raw).replace(/([A-Za-z])\s*\/\s*([A-Za-z])/g, '$1$2').replace(/[⧉•]/g, ' ').replace(/[;,|\t]+/g, ' ')
                    .replace(/\s+/g, ' ').trim();
                if (!line) continue;
                const tm = line.match(/\b([01]?\d|2[0-3]):([0-5]\d)\b/);
                const dm = line.match(/\b(BUY|SELL|CALL|PUT|UP|DOWN)\b/i);
                if (!tm || !dm) continue;
                let dir = dm[1].toUpperCase();
                dir = (dir === 'BUY' || dir === 'CALL' || dir === 'UP') ? 'CALL' : 'PUT';

                // Prefer an explicit market token, including PAIR-OTC / PAIR_OTC / PAIR OTC.
                const tokens = line.match(/[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)?(?:\s*[-_ ]?\s*OTC)?/ig) || [];
                let token = null;
                for (const t of tokens) {
                    const candidate = t.replace(/\s+/g, '').replace(/[-_]OTC$/i, '').replace(/OTC$/i, '');
                    if (/^[A-Za-z]{3,12}$/.test(candidate) && !/^(BUY|SELL|CALL|PUT|UP|DOWN|OTC)$/.test(candidate.toUpperCase())) {
                        if (!token || candidate.length > token.length) token = candidate.toUpperCase();
                        // Prefer a complete currency/asset symbol over a short token.
                        if (token.length >= 6) break;
                    }
                }
                if (!token) continue;
                const isOtc = /\bOTC\b/i.test(line) || /[-_]OTC\b/i.test(line);
                const apiPair = isOtc ? token + '_otc' : token;
                const display = token + (isOtc ? '-OTC' : '');
                const time = tm[1].padStart(2, '0') + ':' + tm[2];
                const key = [apiPair, time, dir].join('|');
                if (seen.has(key)) continue;
                seen.add(key);
                out.push({ pair: apiPair, display, asset: apiPair, asset_display: display, time, direction: dir });
            }
            return out;
        }

        async function runFutureCheck() {
            const input = document.getElementById('fcSignalInput');
            const btn = document.getElementById('fcCheckBtn');
            const status = document.getElementById('fcStatus');
            const signals = parseFcSignals(input ? input.value : '');
            if (!signals.length) {
                if (status) status.innerText = '❌ No valid signals. Paste: ⧉ USDXXX-OTC - 14:45 ⇨ BUY/PUT';
                return;
            }
            const mtgTxt = (document.getElementById('val-fcMtg') || {}).innerText || 'No MTG';
            const mtgMatch = mtgTxt.match(/(\d+)/);
            const mtg = mtgMatch ? Math.min(4, parseInt(mtgMatch[1], 10)) : 0;
            const payTxt = (document.getElementById('val-fcPayout') || {}).innerText || 'All Payout';
            const pm = payTxt.match(/(\d+)/);
            const payoutFilter = pm ? parseInt(pm[1], 10) : 0;
            const dayTxt = ((document.getElementById('val-fcDay') || {}).innerText || 'Today').trim();
            if (btn) { btn.disabled = true; btn.innerText = '⏳ CHECKING...'; }
            if (status) status.innerText = '🔄 Checking ' + signals.length + ' signals...';
            try {
                const res = await fetch(API_BASE + '/future-check', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        signals: signals.map(s => ({ pair: s.pair, asset: s.asset, time: s.time, direction: s.direction, display: s.display, asset_display: s.asset_display })),
                        mtg_level: mtg, payout_filter: payoutFilter, day: dayTxt.toLowerCase()
                    })
                });
                const json = await res.json();
                if (!json.success) throw new Error(json.message || 'Check failed');
                const setText = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
                setText('fcSumWin', json.wins || 0); setText('fcSumLoss', json.losses || 0);
                setText('fcSumTie', json.ties || 0); setText('fcSumPend', json.pending || 0);
                setText('fcSumAcc', (Number(json.accuracy) || 0).toFixed(1) + '%');
                const summary = document.getElementById('fcSummaryBox'); if (summary) summary.style.display = 'block';

                // Match HyperTrade.py's BOT CHECKER output layout and stylized font.
                const M = (typeof toMonospace === 'function') ? toMonospace : (v => v);
                const PM = (typeof fmtPairMono === 'function') ? fmtPairMono : M;
                const DM = (typeof fmtDateMono === 'function') ? fmtDateMono : M;
                const sups = { 1: '¹', 2: '²', 3: '³', 4: '⁴' };
                const fmtTime = t => M(String(t || '').replace(':', '⁚'));
                const fmtPair = a => PM(String(a || '').replace(/[_ ]OTC/i, '-OTC').toUpperCase());
                const fmtDir = d => M(String(d || '').toUpperCase() === 'CALL' ? 'BUY' : 'PUT');
                let resultLines = '';
                (json.results || []).forEach(r => {
                    let sym = '❓';
                    if (!r.checked) sym = '⏳';
                    else if (r.skipped) sym = ' 💰' + M(String(Math.round(r.payout || 0))) + '٪';
                    else if (r.result === 'WIN') sym = '✅' + (r.mtg_used > 0 ? (sups[r.mtg_used] || String(r.mtg_used)) : '');
                    else if (r.result === 'LOSS') sym = '✖️';
                    else if (r.result === 'TIE') sym = '➖';
                    resultLines += '⧉ ' + fmtPair(r.display || r.pair) + ' - ' + fmtTime(r.time) + ' ⇨ ' + fmtDir(r.direction) + ' ' + sym + '\n';
                });
                const acc = (Number(json.accuracy) || 0).toFixed(1);
                const dateStr = String(json.date || '');
                const dateDot = dateStr.replace(/-/g, '.');
                const dateDash = dateStr.replace(/-/g, '—');
                const msg = '▰▱▱ ' + M('BOT CHECKER') + ' ▱▰▰\n'
                    + '  ┏━━━━━━━━━━━┓\n'
                    + '    📆 ' + M(dayTxt.toUpperCase()) + ' — ' + DM(dateDot) + '\n'
                    + '  ┗━━━━━━━━━━━┛\n'
                    + '━━━━━━━━━━━ • ━━━━━━━━━━━\n'
                    + resultLines
                    + '━━━━━━━━━━━ • ━━━━━━━━━━━\n'
                    + '🏆 ' + M('Total') + ' : ' + M(String(json.total_checked || 0)) + '\n'
                    + '✅ ' + M('Win') + ': ' + M(String(json.wins || 0)) + '\n'
                    + '❌ ' + M('Loss') + ': ' + M(String(json.losses || 0)) + '\n'
                    + '🎯 ' + M('Accuracy') + ': ' + DM(acc) + '٪\n'
                    + '🔄 ' + M('MTG') + ': ' + M(String(mtg)) + '\n'
                    + '📅 ' + M('Date') + ': ' + M(dayTxt.toUpperCase()) + ' (' + M(dateDash) + ')\n'
                    + '━━━━━━━━━━━ • ━━━━━━━━━━━';
                const card = document.getElementById('fcResultCard');
                if (card) { card.innerText = msg; card.classList.add('show'); card.style.display = 'block'; }
                const copyBox = document.getElementById('fcCopyBox'); if (copyBox) copyBox.style.display = 'block';
                window.__fcLastResult = msg;
                if (status) { status.innerText = '✅ ' + (json.total_checked || 0) + ' signal check complete'; }
            } catch (e) {
                if (status) status.innerText = '❌ ' + (e.message || e);
            } finally {
                if (btn) { btn.disabled = false; btn.innerText = '🚀 CHECK SIGNALS'; }
            }
        }

        function fcCopyResult() {
            const card = document.getElementById('fcResultCard');
            if (!card || !card.innerText) return;
            navigator.clipboard.writeText(card.innerText).then(function(){ showToast('Result copied!'); }).catch(function(){});
        }

        window.runFutureCheck = runFutureCheck;
        window.fcLoadSample = fcLoadSample;
        window.fcCopyResult = fcCopyResult;

        lucide.createIcons();
    </script>
</body>
</html>"""

# Minimal boot loader page — contains NO app UI source. The real UI (UI_HTML)
# is delivered ONLY over the /ws WebSocket after an explicit ui_request.
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta name="robots" content="noindex, nofollow" />
    <title>HyperTrade — RAVITH AI PRO</title>
    <style>
        html, body { margin: 0; height: 100%; background: #04060d; overflow: hidden; }
        #rv-boot { position: fixed; inset: 0; display: flex; flex-direction: column; align-items: center;
            justify-content: center; gap: 18px; font-family: monospace; z-index: 5; }
        .rv-ring { width: 52px; height: 52px; border-radius: 50%;
            border: 3px solid rgba(0, 242, 254, .12); border-top-color: #00F2FE;
            animation: rvspin 0.9s linear infinite; }
        @keyframes rvspin { to { transform: rotate(360deg); } }
        .rv-txt { color: #00F2FE; font-size: 12px; letter-spacing: 3px; text-transform: uppercase;
            animation: rvblink 1.2s ease-in-out infinite; }
        @keyframes rvblink { 50% { opacity: .35; } }
        .rv-err { color: #ff3d71; font-size: 12px; display: none; max-width: 80%; text-align: center; line-height: 1.7; }
        #rv-frame { position: fixed; inset: 0; width: 100%; height: 100%; border: 0; display: none; }
    </style>
</head>
<body>
    <div id="rv-boot">
        <div class="rv-ring"></div>
        <div class="rv-txt" id="rv-msg">Secure channel…</div>
        <div class="rv-err" id="rv-err"></div>
    </div>
    <iframe id="rv-frame" title="app"></iframe>
    <script>
    (function () {
        var msg = document.getElementById('rv-msg'), err = document.getElementById('rv-err');
        function fail(t) { msg.style.display = 'none'; err.style.display = 'block'; err.textContent = t; }
        var proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
        var ws;
        try { ws = new WebSocket(proto + location.host + '/ws'); }
        catch (e) { fail('WebSocket unsupported in this browser.'); return; }
        var got = false;
        ws.onopen = function () { try { ws.send(JSON.stringify({ type: 'ui_request' })); } catch (e) {} };
        ws.onmessage = function (ev) {
            try {
                var d = JSON.parse(ev.data);
                if (d && d.type === 'ui_html' && typeof d.html === 'string' && d.html.length > 100) {
                    got = true;
                    var f = document.getElementById('rv-frame');
                    f.style.display = 'block';
                    f.srcdoc = d.html;
                    f.onload = function () { var b = document.getElementById('rv-boot'); if (b) b.remove(); };
                    setTimeout(function () { var b = document.getElementById('rv-boot'); if (b) b.remove(); }, 12000);
                }
            } catch (e) {}
        };
        ws.onerror = function () { if (!got) fail('Connection failed. Server unreachable or blocked.'); };
        ws.onclose = function () { if (!got) fail('Secure channel closed before UI delivery.'); };
        setTimeout(function () { if (!got) fail('Timeout — server did not respond.'); }, 20000);
    })();
    </script>
</body>
</html>"""


# ==========================================
# 1. QUOTEX & MARKET SETTINGS
# ==========================================
# Set BOT_TOKEN in Railway Variables (never place the token in source code).
# Quotex login is done from Telegram:  /start -> SSID token -> CSRF token
# There is NO e-mail/password, NO ADMIN_ID, NO owner ID, NO API key needed.
import requests  # Telegram control bot HTTP

DATA_DIR = Path(os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
                or str(Path(__file__).resolve().parent / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


def _load_bot_config():
    try:
        with open(DATA_DIR / "bot_config.json", "r") as f:
            cfg = json.load(f)
        if isinstance(cfg, dict):
            return cfg
    except Exception:
        pass
    return {}


_BOT_CFG = _load_bot_config()
# Session login: SSID (token) + CSRF (XSRF-TOKEN). No e-mail/password anywhere.
QUOTEX_SSID_TOKEN = (os.getenv("QUOTEX_SSID_TOKEN") or _BOT_CFG.get("ssid_token") or "").strip()
QUOTEX_CSRF_TOKEN = (os.getenv("QUOTEX_CSRF_TOKEN") or _BOT_CFG.get("csrf_token") or "").strip()
QUOTEX_USER_AGENT = (os.getenv("QUOTEX_USER_AGENT") or _BOT_CFG.get("user_agent") or "Quotex/1.0").strip()
USE_DEMO = bool(_BOT_CFG.get("use_demo", True))
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "5000"))
MAX_CANDLES = 5000

UTC_PLUS_6 = pytz.timezone('Asia/Dhaka')

# Global Storage: { "PAIR_TIMEFRAME": deque(maxlen=5000) }
MARKET_DATA = {}
ALL_INSTRUMENTS = []
q_instance = None
PAYOUT_HISTORY = {}  # { "PAIR_TIMEFRAME": { "timestamp": payout } }

# ===== PERSISTENT SIGNAL ARROW STORE (arrows lock to their candle; cleared ONLY by RESET) =====
SIGNAL_HISTORY = {}           # { "pair": { "YYYY-MM-DD HH:MM:SS": "BUY/SELL" } }
SIGNALS_FILE = str(DATA_DIR / "signals_data.json")
signals_lock = threading.Lock()

# ===== ADMIN PANEL — owner password (hardcoded & secure inside this file) =====
ADMIN_PASSWORD = "RavithXs"

# ===== DATA-FEED STATE (admin LOGOUT/RELOGIN control for the collection account) =====
BOT_FEED_STATE = {"logged_in": False, "status": "offline"}


def save_bot_config():
    try:
        atomic_json(DATA_DIR / "bot_config.json", {
            "ssid_token": QUOTEX_SSID_TOKEN,
            "csrf_token": QUOTEX_CSRF_TOKEN,
            "user_agent": QUOTEX_USER_AGENT,
            "use_demo": USE_DEMO,
        })
    except Exception as e:
        print(f"[bot_config save error] {e}")


def set_feed_session(ssid, csrf):
    """Store a manual Quotex web session (token + CSRF) and request a fresh connect."""
    global QUOTEX_SSID_TOKEN, QUOTEX_CSRF_TOKEN
    QUOTEX_SSID_TOKEN = (ssid or "").strip()
    QUOTEX_CSRF_TOKEN = (csrf or "").strip()
    BOT_FEED_STATE["logged_in"] = bool(QUOTEX_SSID_TOKEN)
    BOT_FEED_STATE["status"] = "starting" if QUOTEX_SSID_TOKEN else "offline"
    save_bot_config()


def build_quotex_client():
    """Build a pyquotex client from the SSID/CSRF session tokens only."""
    if not QUOTEX_SSID_TOKEN:
        raise RuntimeError("Quotex session token missing. Telegram e /start diye token+CSRF din.")
    client = Quotex(lang="en", ssid_token=QUOTEX_SSID_TOKEN,
                    csrf_token=QUOTEX_CSRF_TOKEN or None,
                    user_agent=QUOTEX_USER_AGENT)
    client.set_token_csrf(QUOTEX_SSID_TOKEN, QUOTEX_CSRF_TOKEN or None,
                          user_agent=QUOTEX_USER_AGENT)
    return client

# ===== RUNNING CANDLE ENGINE STATE (Chart.py logic) =====
RUNNING_CANDLES = {}  # { "PAIR": { "1m": {"start","open","high","low","close"} } }
TIMEFRAMES = {"5s": 5, "10s": 10, "15s": 15, "30s": 30, "1m": 60, "2m": 120, "3m": 180,
              "5m": 300, "10m": 600, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}
CHART_BACKGROUND_IMAGE_URL = "https://ik.imagekit.io/x5w5qvwgy/5480daadd66215acc0dd40e7d87bdd77.jpg"

# ==========================================
# 2. ACCESS GATE SETTINGS (single shared password entry)
# ==========================================
APP_PASSWORD = "RavithXs"   # Standard access → 3 free credits
# PRO access password — gives unlimited credits. Fully server-side validated.
PRO_ACCESS_PASSWORD = "F*ck_You"
SHARED_USER_EMAIL = "ravith@hypertrade.local"

USERS_FILE = str(DATA_DIR / "users_data.json")
DEFAULT_FREE_CREDITS = 3

file_lock = threading.Lock()

# ===== SESSION STORE & REAL-TIME BAN EVENT SUBSCRIBERS =====
ACTIVE_SESSIONS = {}      # {email: set(session_tokens)}
BAN_SUBSCRIBERS = {}      # {email: [queue.Queue, ...]}  (SSE clients of that account)
BAN_SUB_LOCK = threading.Lock()

def issue_session(email):
    token = "%016x" % int.from_bytes(os.urandom(8), "big")
    ACTIVE_SESSIONS.setdefault(email, set()).add(token)
    return token

def drop_sessions(email):
    ACTIVE_SESSIONS.pop(email, None)

def broadcast_ban(email, message):
    """Push a BAN event to every open browser/tab session of this account (real-time)."""
    with BAN_SUB_LOCK:
        subs = list(BAN_SUBSCRIBERS.get(email, []))
    dead = []
    for q in subs:
        try:
            q.put_nowait({"type": "ban", "message": message})
        except Exception:
            dead.append(q)
    if dead:
        with BAN_SUB_LOCK:
            for q in dead:
                try:
                    BAN_SUBSCRIBERS.get(email, []).remove(q)
                except Exception:
                    pass
    print(f"\U0001f6ab [BAN EVENT] pushed to {len(subs)} active client(s): {email}")

DEFAULT_SETTINGS = {
    "market": "USDBDT-OTC",
    "timeframe": "1 Minute",
    "strategy": "AI Smart Signal",
    "chartType": "Candlestick",
    "chartStyle": "Style 1 - Classic",
    "uiStyle": "UI 1 - Classic",
    "martingale": "No MTG",
    "dialogAnim": "Scale",
    "signalMode": "Manual",
    "telegram": "@Mahabub_iX",
    "botToken": "",
    "chatId": "",
    "darkMode": True,
    "autoTelegram": True,
    "soundAlerts": True,
    "vibration": True,
    "speed": "2",
    "glass": "0.8",
    "fontSize": "12",
    "dashboardName": "RAVITH PRO",
    "watermarkText": "\U0001d411\U0001d400\U0001d40f\U0001d408\U0001d413\U0001d407 \U0001d412\U0001d412",
    "signalName": "RAVITH AI PRO",
    "autoMarkets": [],
    "stats": {"wins": 0, "losses": 0, "streakW": 0, "streakL": 0},
    "tradeHistory": [],
    "uiTheme": "default",
    "backgroundMedia": "",
    "backgroundType": "",
    "showIndicators": True,
    "showCountdown": True,
    "showTerminal": True,
    "showWinLoss": True,
    "autoAnalyze": True,
    "candleAlerts": True,
    "fcDay": "Today",
    "fcMtg": "No MTG",
    "fcPayout": "All Payout"
}

# ==========================================
# INITIALIZE FLASK
# ==========================================
app = Flask(__name__)
CORS(app)
sock = Sock(app)


# ==========================================
# HELPER FUNCTIONS: AUTH & UTILS
# ==========================================
def get_secure_6_digit():
    """Generate a random 6-digit number without using the random library"""
    num = int.from_bytes(os.urandom(4), 'big')
    return (num % 900000) + 100000

def load_users():
    with file_lock:
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_users(users):
    # Atomic write: temp file + os.replace — a crash mid-write can never
    # corrupt users_data.json again (root cause of lost user data).
    with file_lock:
        tmp = USERS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(users, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, USERS_FILE)

def generate_uid():
    """Generate a unique 6-digit UID"""
    users = load_users()
    existing_uids = [u.get("uid", "") for u in users.values()]
    while True:
        uid = str(get_secure_6_digit())
        if uid not in existing_uids:
            return uid

def get_user_by_uid(uid):
    users = load_users()
    for email, data in users.items():
        if data.get("uid") == uid:
            return email, data
    return None, None


# ==========================================
# HELPER FUNCTIONS: QUOTEX BACKGROUND SYNC# HELPER FUNCTIONS: QUOTEX BACKGROUND SYNC
# ==========================================
def ts_to_dt(ts):
    if ts is None:
        return None
    try:
        ts = int(ts)
        if ts > 1_000_000_000_000:
            ts = ts / 1000
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt_utc.astimezone(UTC_PLUS_6)
    except:
        return None

def parse_timeframe(tf_str: str) -> int:
    if not tf_str:
        return 60
    tf_str = tf_str.lower().strip()
    try:
        if tf_str.endswith('s'): return int(tf_str[:-1])
        elif tf_str.endswith('m'): return int(tf_str[:-1]) * 60
        elif tf_str.endswith('h'): return int(tf_str[:-1]) * 3600
        return int(tf_str)
    except:
        return 60

def get_payout(q, pair_name):
    if not q or not hasattr(q, "api") or not q.api or not hasattr(q.api, "instruments"):
        return 0.0
    for inst in q.api.instruments:
        if len(inst) > 1 and inst[1] == pair_name:
            if len(inst) > 18 and inst[18] is not None: return float(inst[18])
            if len(inst) > 5 and inst[5] is not None: return float(inst[5])
            for value in reversed(inst):
                if isinstance(value, (int, float)) and 0 <= value <= 100:
                    return float(value)
            return 0.0
    return 0.0

def get_payout_for_time(pair, timeframe, time_str):
    storage_key = f"{pair}_{timeframe}"
    if storage_key in PAYOUT_HISTORY:
        payout_times = list(PAYOUT_HISTORY[storage_key].keys())
        if payout_times:
            if time_str in PAYOUT_HISTORY[storage_key]:
                return PAYOUT_HISTORY[storage_key][time_str]
            else:
                sorted_times = sorted(payout_times)
                for t in reversed(sorted_times):
                    if t <= time_str:
                        return PAYOUT_HISTORY[storage_key][t]
    return 0.0

def update_payout_history(pair, timeframe, time_str, payout):
    storage_key = f"{pair}_{timeframe}"
    if storage_key not in PAYOUT_HISTORY:
        PAYOUT_HISTORY[storage_key] = {}
    PAYOUT_HISTORY[storage_key][time_str] = payout

def detect_markets(q):
    if not q or not hasattr(q, "api") or not q.api:
        return []
    markets = []
    seen = set()
    try:
        for inst in q.api.instruments:
            if len(inst) < 2:
                continue
            pair = str(inst[1]).strip()
            if not pair or pair in seen:
                continue
            seen.add(pair)
            payout = get_payout(q, pair)
            pair_upper = pair.upper()

            if pair.endswith("_otc") or pair.endswith("_OTC"): category = "OTC"
            elif any(x in pair_upper for x in ["BTC","ETH","LTC","BNB","SOL","DOGE","XRP","ADA","DOT","TRX","AVAX"]): category = "Crypto"
            elif any(x in pair_upper for x in ["XAU","XAG","WTI","BRENT","NGAS"]): category = "Commodity"
            elif any(x in pair_upper for x in ["US30","NAS100","SPX","GER40","UK100","JP225","AUS200","FR40","EU50"]): category = "Index"
            else: category = "Forex"

            markets.append({
                "pair": pair,
                "display_name": pair.replace("_otc", "").replace("_OTC", ""),
                "payout": payout,
                "category": category,
            })
    except Exception as e:
        print(f"❌ Market Detection Error: {e}")
    return sorted(markets, key=lambda x: x["pair"])

async def safe_fetch(q, pair, period):
    """Fetch historical candles from Quotex. Tries multiple pyquotex API shapes."""
    end_from = time.time()
    offset = 120
    try:
        raw = await q.get_candles(pair, end_from, offset, period)
        if raw:
            return raw
    except Exception:
        pass
    try:
        raw = await q.get_candles(pair, period)
        if raw:
            return raw
    except Exception:
        pass
    try:
        raw = await q.get_candle_v2(pair, period)
        if raw:
            return raw
    except Exception:
        pass
    try:
        raw = await q.get_candle_v2(pair, end_from, offset, period)
        if raw:
            return raw
    except Exception:
        pass
    return None

def load_signals():
    global SIGNAL_HISTORY
    try:
        with open(SIGNALS_FILE, "r") as f:
            SIGNAL_HISTORY = json.load(f)
    except Exception:
        SIGNAL_HISTORY = {}

def save_signals():
    try:
        with open(SIGNALS_FILE, "w") as f:
            json.dump(SIGNAL_HISTORY, f)
    except Exception as e:
        print(f"[signals save error] {e}")

def lookup_signal(pair, time_str):
    try:
        return SIGNAL_HISTORY.get(pair, {}).get(time_str, "")
    except Exception:
        return ""

def register_signal(pair, time_str, direction):
    with signals_lock:
        SIGNAL_HISTORY.setdefault(pair, {})[time_str] = direction.upper()
        keys = sorted(SIGNAL_HISTORY[pair].keys())
        if len(keys) > 500:
            for k in keys[:-500]:
                SIGNAL_HISTORY[pair].pop(k, None)
        save_signals()

def clear_signals(pair=None):
    with signals_lock:
        if pair:
            SIGNAL_HISTORY.pop(pair, None)
        else:
            SIGNAL_HISTORY.clear()
        save_signals()


def update_market_data(storage_key, candle_data):
    if storage_key not in MARKET_DATA:
        MARKET_DATA[storage_key] = deque(maxlen=MAX_CANDLES)
    
    existing = list(MARKET_DATA[storage_key])
    found = False
    for i, c in enumerate(existing):
        if c["time"] == candle_data["time"]:
            existing[i] = candle_data
            found = True
            break
    if not found:
        existing.append(candle_data)
    
    unique = {c["time"]: c for c in existing}
    sorted_data = sorted(unique.values(), key=lambda x: x["time"], reverse=True)
    
    new_deque = deque(maxlen=MAX_CANDLES)
    for c in sorted_data:
        new_deque.append(c)
    MARKET_DATA[storage_key] = new_deque


# ==========================================
# RUNNING CANDLE ENGINE (ported from Chart.py) — FIXED
# ==========================================
def get_last_closed_candle(pair, frame):
    """Get the most recent closed candle for a given pair/frame."""
    # We store only 1m candles, so we'll use that as the source for all timeframes
    # (higher timeframe closed candles could be built from 1m, but for simplicity we use 1m)
    storage_key = f"{pair}_1m"
    if storage_key in MARKET_DATA and MARKET_DATA[storage_key]:
        # MARKET_DATA stores newest first
        for candle in MARKET_DATA[storage_key]:
            # Return the first candle that is fully closed (we assume all are closed)
            return candle
    return None

def _promote_running_candle(asset, frame, rc):
    """When a candle finishes, move it into MARKET_DATA instantly — real-time, no fetch lag."""
    try:
        if frame != "1m":
            return  # only 1m candles are stored
        storage_key = f"{asset}_1m"
        dt = ts_to_dt(rc["start"])
        if dt is None:
            return
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        payout = get_payout_for_time(asset, "1m", time_str) if storage_key in PAYOUT_HISTORY else 0.0
        candle_data = {
            "close": rc["close"],
            "high": rc["high"],
            "low": rc["low"],
            "open": rc["open"],
            "pair": asset.replace('_otc', '-OTC').upper(),
            "signal": lookup_signal(asset, time_str),  # arrow ONLY if a signal was locked on this candle
            "time": time_str,
            "payout": payout
        }
        update_market_data(storage_key, candle_data)
    except Exception as e:
        print(f"[promote error] {e}")


def update_running_candle(asset, frame, price, ts_sec):
    """Build REAL-TIME running candle from each Quotex price tick.
    - open = previous candle close (gap-free)
    - high/low/close update on every tick
    - when minute rolls over, previous running candle is promoted to MARKET_DATA"""
    asset = _norm_asset(asset)
    if not asset or price is None:
        return
    try:
        price = float(price)
    except Exception:
        return
    if price <= 0:
        return
    duration = TIMEFRAMES.get(frame, 60)
    try:
        ts_sec = int(ts_sec)
    except Exception:
        ts_sec = int(time.time())
    candle_start = (ts_sec // duration) * duration
    if asset not in RUNNING_CANDLES:
        RUNNING_CANDLES[asset] = {}
    curr = RUNNING_CANDLES[asset].get(frame)

    if not curr or curr.get("start") != candle_start:
        if curr:
            _promote_running_candle(asset, frame, curr)
        prev_candle = get_last_closed_candle(asset, frame)
        prev_close = prev_candle["close"] if prev_candle else price
        RUNNING_CANDLES[asset][frame] = {
            "start": candle_start,
            "open": float(prev_close),
            "high": max(float(prev_close), price),
            "low": min(float(prev_close), price),
            "close": price,
            "ticks": 1,
            "updated": time.time(),
        }
    else:
        if price > curr["high"]:
            curr["high"] = price
        if price < curr["low"]:
            curr["low"] = price
        curr["close"] = price
        curr["ticks"] = int(curr.get("ticks") or 0) + 1
        curr["updated"] = time.time()

def _norm_asset(asset):
    """Normalize Quotex asset id so ticks always map to MARKET_DATA keys."""
    if not asset:
        return ""
    a = str(asset).strip().replace("-", "_").replace(" ", "_")
    # USDPHP_otc / usdphp_otc / USDPHP-OTC
    if a.lower().endswith("_otc"):
        base = a[:-4]
        return base.upper() + "_otc"
    if a.upper().endswith("OTC") and "_" not in a:
        return a[:-3].upper() + "_otc"
    return a

def process_message(message):
    """Parse Quotex websocket ticks → REAL-TIME running candle (open/high/low/close)."""
    try:
        text = message.decode('utf-8', errors='ignore') if isinstance(message, bytes) else str(message)
        match = re.search(r'\[\[\s*("([^"]+)"|null)?,?\s*([\d.]+)\s*,\s*([\d.]+)', text)
        if match:
            asset_raw = match.group(2) if match.group(2) else None
            timestamp = float(match.group(3))
            price = float(match.group(4))
            if asset_raw and price > 0:
                asset = _norm_asset(asset_raw)
                ts_sec = int(timestamp // 1000) if timestamp > 1_000_000_000_000 else int(timestamp)
                for frame in TIMEFRAMES:
                    update_running_candle(asset, frame, price, ts_sec)
                return
        if text.startswith('[') or text.startswith('{'):
            try:
                payload = json.loads(text)
            except Exception:
                payload = None
            items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                asset_raw = item.get('asset') or item.get('symbol') or item.get('pair')
                price = item.get('price') or item.get('close') or item.get('bid') or item.get('value')
                ts = item.get('time') or item.get('timestamp') or item.get('t') or time.time()
                if not asset_raw or price is None:
                    continue
                try:
                    price = float(price)
                    ts_sec = int(float(ts))
                    if ts_sec > 1_000_000_000_000:
                        ts_sec //= 1000
                except Exception:
                    continue
                if price > 0:
                    asset = _norm_asset(str(asset_raw))
                    for frame in TIMEFRAMES:
                        update_running_candle(asset, frame, price, ts_sec)
    except Exception as e:
        print(f"[tick error] {e}")


def running_to_api(pair, frame):
    """Convert internal running candle → public candle dict (real-time OHLC)."""
    pair = _norm_asset(pair)
    rc = RUNNING_CANDLES.get(pair, {}).get(frame)
    if not rc:
        return None
    dt = ts_to_dt(rc["start"])
    time_str = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""
    return {
        "close": float(rc["close"]),
        "high": float(rc["high"]),
        "low": float(rc["low"]),
        "open": float(rc["open"]),
        "pair": pair.replace('_otc', '-OTC').upper(),
        "signal": lookup_signal(pair, time_str),
        "time": time_str,
        "payout": 0.0,
        "is_running": True,
        "ticks": int(rc.get("ticks") or 0),
        "updated": float(rc.get("updated") or 0),
    }

def get_candles_with_running(pair, timeframe, limit):
    """Return (closed candles newest-first, live running candle).
    Running candle is ALWAYS the current real-time 1m candle from Quotex ticks.
    It is never duplicated inside the closed list."""
    frame = timeframe if timeframe in TIMEFRAMES else "1m"
    pair = _norm_asset(pair) if pair else pair
    storage_key = f"{pair}_{timeframe}"
    if storage_key in MARKET_DATA:
        closed = list(MARKET_DATA[storage_key])
    else:
        fallback_key = f"{pair}_1m"
        closed = list(MARKET_DATA[fallback_key]) if fallback_key in MARKET_DATA else []

    running = running_to_api(pair, frame)

    # If we have a running candle, drop any closed candle with the same start time
    # (that slot is still forming — real-time OHLC comes from RUNNING_CANDLES)
    if running and running.get("time"):
        closed = [c for c in closed if c.get("time") != running.get("time")]

    closed = closed[:limit]
    for c in closed:
        sig = lookup_signal(pair, c.get("time", ""))
        if sig:
            c["signal"] = sig
    if running and closed:
        running["payout"] = closed[0].get("payout", 0.0)
    elif running:
        running["payout"] = running.get("payout", 0.0)
    return closed, running


# ==========================================
# QUOTEX BACKGROUND LOOP (unchanged)
# ==========================================
async def background_market_loop():
    """Data-collection loop. Reconnects automatically; supports admin LOGOUT/RELOGIN
    via BOT_FEED_STATE. Chart API reads from MARKET_DATA/RUNNING_CANDLES which this
    loop keeps fresh from the live Quotex tick stream."""
    global q_instance, ALL_INSTRUMENTS, AUTO_TRADE_LOOP, USE_DEMO, QUOTEX_SSID_TOKEN, QUOTEX_CSRF_TOKEN
    AUTO_TRADE_LOOP = asyncio.get_running_loop()
    period = 60

    while True:
        # ----- (Re)load session each cycle — Telegram /start or admin RELOGIN updates bot_config.json -----
        cfg = _load_bot_config()
        if cfg.get("ssid_token") and cfg.get("ssid_token") != QUOTEX_SSID_TOKEN:
            QUOTEX_SSID_TOKEN = str(cfg.get("ssid_token") or "").strip()
            QUOTEX_CSRF_TOKEN = str(cfg.get("csrf_token") or "").strip()
            BOT_FEED_STATE["logged_in"] = bool(QUOTEX_SSID_TOKEN)
        USE_DEMO = bool(cfg.get("use_demo", USE_DEMO))

        if not BOT_FEED_STATE.get("logged_in") or not QUOTEX_SSID_TOKEN:
            BOT_FEED_STATE["status"] = "offline"
            await asyncio.sleep(5)
            continue

        try:
            q = build_quotex_client()
        except Exception as e:
            BOT_FEED_STATE["status"] = "error"
            print(f"❌ Quotex token setup error: {e}")
            await asyncio.sleep(10)
            continue

        print("🔌 Connecting to Quotex using SSID/CSRF session...")
        BOT_FEED_STATE["status"] = "connecting"
        try:
            connect_result = await asyncio.wait_for(q.connect(), timeout=45)
            if isinstance(connect_result, tuple):
                ok = bool(connect_result[0])
                reason = connect_result[1] if len(connect_result) > 1 else ""
            else:
                ok, reason = bool(connect_result), ""
            if ok and hasattr(q, "check_connect"):
                try:
                    chk = await q.check_connect()
                    if chk is False:
                        ok = False
                        reason = reason or "check_connect failed"
                except Exception:
                    pass
        except Exception as e:
            print(f"❌ Data-feed connect error: {e}")
            ok, reason = False, str(e)
        if not ok:
            print(f"❌ Data-feed login failed! {reason or 'Check credentials'}. Retrying in 10s...")
            BOT_FEED_STATE["status"] = "error"
            try:
                await q.close()
            except Exception:
                pass
            await asyncio.sleep(10)
            continue

        print("✅ Data-feed login successful! Starting real-time data collection...")
        try:
            if hasattr(q, "change_account"):
                await q.change_account("PRACTICE" if USE_DEMO else "REAL")
            elif hasattr(q, "set_account_mode"):
                q.set_account_mode("practice" if USE_DEMO else "real")
        except Exception as e:
            print(f"⚠️ account mode switch: {e}")
        q_instance = q
        BOT_FEED_STATE["status"] = "online"
        BOT_FEED_STATE["logged_in"] = True

        # Hook Quotex websocket ticks -> running candle engine
        try:
            ws_app = q.api.websocket_client.wss
            _orig_on_message = getattr(ws_app, 'on_message', None)
            def _tick_handler(ws, msg):
                try:
                    process_message(msg)
                except Exception as _e:
                    print(f"⚠️ tick handler error: {_e}")
                if _orig_on_message:
                    try:
                        return _orig_on_message(ws, msg)
                    except:
                        pass
            ws_app.on_message = _tick_handler
            print("✅ Real-time tick handler attached (running candle engine active)")
        except Exception as e:
            print(f"⚠️ Tick handler attach failed: {e}")

        # ----- inner fetch cycle: runs until logout / error -----
        while BOT_FEED_STATE.get("logged_in"):
            try:
                instruments = detect_markets(q)
                if instruments:
                    ALL_INSTRUMENTS = instruments

                pairs = [m["pair"] for m in ALL_INSTRUMENTS] if ALL_INSTRUMENTS else ["USDPHP_otc", "USDARS_otc", "USDBRL_otc"]
                for pair in pairs:
                    current_payout = get_payout(q, pair)
                    raw_candles = await safe_fetch(q, pair, period)
                    if not raw_candles:
                        continue

                    storage_key = f"{pair}_1m"
                    for r in raw_candles:
                        ts = r.get("time") or r.get("timestamp") or r.get("t") or r.get("date")
                        dt = ts_to_dt(ts)
                        if dt is None: continue
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    
                        if storage_key in PAYOUT_HISTORY and time_str in PAYOUT_HISTORY[storage_key]:
                            payout_for_time = PAYOUT_HISTORY[storage_key][time_str]
                        else:
                            payout_for_time = current_payout
                            update_payout_history(pair, "1m", time_str, payout_for_time)

                        open_p = float(r.get("open") or r.get("o", 0))
                        close_p = float(r.get("close") or r.get("c", 0))
                    
                        candle_data = {
                            "close": close_p,
                            "high": float(r.get("high") or r.get("h", 0)),
                            "low": float(r.get("low") or r.get("l", 0)),
                            "open": open_p,
                            "pair": pair.replace('_otc', '-OTC').upper(),
                            "signal": lookup_signal(pair, time_str),
                            "time": time_str,
                            "payout": payout_for_time
                        }
                        update_market_data(storage_key, candle_data)
                        try:
                            # Seed / refresh running candle using server time so chart
                            # always has a live forming candle even before the next tick
                            update_running_candle(pair, "1m", close_p, int(time.time()))
                        except Exception:
                            pass

                    await asyncio.sleep(0.05)
                print(f"🔄 [Cycle Complete] markets={len(pairs)} keys={len(MARKET_DATA)} running={len(RUNNING_CANDLES)} status={BOT_FEED_STATE.get('status')}")
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"⚠️ Error in background loop: {e}")
                await asyncio.sleep(5)

        # ----- admin logged out or feed dropped: tear down & wait for relogin -----
        BOT_FEED_STATE["status"] = "offline"
        if q_instance is q:
            q_instance = None
        try:
            await q.close()
        except Exception:
            pass
        await asyncio.sleep(3)


def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(background_market_loop())


# ==========================================
# SERVER-SIDE BAN / SESSION ENFORCEMENT (every protected user route)
# ==========================================
BAN_GUARDED_PATHS = {
    "/profile", "/use-credit", "/save-settings", "/get-settings", "/reset-results",
    "/save-signal", "/clear-signals", "/record-result", "/trade-history", "/session-remember",
    "/quotex-login", "/quotex-status", "/quotex-disconnect",
    "/auto-trade", "/auto-trade/decision", "/auto-trade/cancel"
}

@app.before_request
def enforce_ban_and_session():
    if request.path not in BAN_GUARDED_PATHS:
        return None
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or request.args.get("email") or "").strip()
    if not email:
        return None
    user = load_users().get(email)
    if not user:
        drop_sessions(email)
        print(f"\u26d4 [GUARD] account not found in database: {email} -> forcing auto-logout")
        return jsonify({"success": False, "account_deleted": True,
                        "message": "Your account is no longer registered on this server. You have been logged out."}), 401
    if user.get("banned"):
        drop_sessions(email)
        print(f"\u26d4 [GUARD] blocked request {request.path} from banned account: {email}")
        return jsonify({"success": False, "banned": True,
                        "message": "Your account has been banned by the administrator. Contact support: @MAHBAUB_iX"}), 403
    token = data.get("session") or request.headers.get("X-Session")
    if token and token not in ACTIVE_SESSIONS.get(email, set()):
        return jsonify({"success": False, "session_expired": True,
                        "message": "Session terminated. Please login again."}), 401
    return None

# ==========================================
# HYBRID ROUTE (`/`) -> Serves Candles OR Index
# ==========================================
@app.route('/', methods=['GET'])
def index_or_candles():
    """
    If 'Pair' parameter exists, act as the Candle API.
    Otherwise, act as the General App API Index.
    """
    pair = request.args.get('Pair') or request.args.get('pair')
    
    # 1. CANDLE LOGIC
    if pair:
        candle_limit = request.args.get('Candle') or request.args.get('candle') or 5000
        timeframe = request.args.get('Time') or request.args.get('time') or "1m"
        try:
            candle_limit = int(candle_limit)
        except:
            candle_limit = 5000

        # Closed candles + REAL running candle (built from live Quotex ticks)
        data_list, running = get_candles_with_running(pair, timeframe, candle_limit)

        return jsonify({
            "api_pair": pair,
            "timeframe": timeframe,
            "count": len(data_list),
            "data": data_list,
            "running": running
        })
        
    # 2. JSON API INDEX (kept for developers) -> use /?json=1
    if request.args.get('json') or request.args.get('api'):
        return jsonify({
        "success": True,
        "service": "RAVITH TRADING UNIFIED API",
        "endpoints": [
            "/?Pair=USDBDT_otc&Time=1m (Get Candles + running)",
            "/chart_image?Pair=USDBDT_otc&Candle=60&SS=RAVITH-PRO (Chart SS Image)",
            "/markets", "/latest", "/payout-history",
            "/login", "/profile", "/use-credit", "/session-remember",
            "/save-settings", "/get-settings",
            "/total-users", "/users", "/set-credit", "/remove", "/block", "/unblock",
            "/admin-login", "/save-signal", "/clear-signals"
        ]
        })

    # 3. WEB UI LOGIC -> Direct URL open korle SUDHU boot loader page jabe.
    # Asol UI kono HTTP response-e nei — sudhu /ws WebSocket diye delivery hoy.
    r = app.make_response(INDEX_HTML)
    r.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    r.headers['Pragma'] = 'no-cache'
    r.headers['X-Content-Type-Options'] = 'nosniff'
    r.headers['X-Frame-Options'] = 'SAMEORIGIN'
    r.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
    return r


# ==========================================
# SESSION REMEMBER (login save) — saved session thakle server restart / tab
# close er poreo session token re-issue kore dey, jeno URL open korlei
# barbar login request na ashe (user request: ekbar login = always logged in).
# ==========================================
@app.route("/session-remember", methods=["POST"])
def session_remember_route():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400
    users = load_users()
    user = users.get(email)
    if not user:
        drop_sessions(email)
        return jsonify({"success": False, "account_deleted": True,
                        "message": "Your account is no longer registered on this server. You have been logged out."}), 401
    if user.get("banned"):
        drop_sessions(email)
        return jsonify({"success": False, "banned": True,
                        "message": "Your account has been banned by the administrator."}), 403
    token = data.get("session") or request.headers.get("X-Session")
    sessions = ACTIVE_SESSIONS.setdefault(email, set())
    if token and token in sessions:
        return jsonify({"success": True, "session": token, "reused": True})
    new_token = issue_session(email)
    return jsonify({"success": True, "session": new_token, "reused": False})



# ==========================================
# FUTURE CHECKER API
# ==========================================
def _fc_time_to_min(t):
    try:
        hh, mm = str(t).strip().split(":")
        hh_i, mm_i = int(hh), int(mm)
        if 0 <= hh_i <= 23 and 0 <= mm_i <= 59:
            return hh_i * 60 + mm_i
    except Exception:
        pass
    return None


def _fc_check_one(closed, running, mkt_today, sig_time, direction, mtg_level):
    base_min = _fc_time_to_min(sig_time)
    if base_min is None:
        return {"result": "UNKNOWN", "mtg_used": 0, "checked": False, "error": "Invalid time", "payout": 0}

    def candle_win(c, d):
        if c is None:
            return None
        try:
            op = float(c.get("open")); cl = float(c.get("close"))
        except Exception:
            return None
        if op == cl:
            return None
        return (cl > op) if d in ("CALL", "BUY") else (cl < op)

    def find_at(total_min):
        if total_min < 0:
            return None
        hh_s = "%02d:%02d" % (total_min // 60, total_min % 60)
        target_prefix = mkt_today + " " + hh_s
        for c in closed:
            if str(c.get("time", "")).startswith(target_prefix):
                return c
        if running and str(running.get("time", "")).startswith(target_prefix):
            return running
        return None

    entry = find_at(base_min)
    if entry is None:
        return {"result": "PENDING", "mtg_used": 0, "checked": False, "error": "Candle not found", "payout": 0}
    try:
        payout = float(entry.get("payout") or 0)
    except Exception:
        payout = 0.0
    win = candle_win(entry, direction)
    if win is None:
        return {"result": "TIE", "mtg_used": 0, "checked": True, "payout": payout}
    if win:
        return {"result": "WIN", "mtg_used": 0, "checked": True, "payout": payout}
    mtg_used = 0
    mtg_win = False
    if mtg_level >= 1:
        for lvl in range(1, min(int(mtg_level), 4) + 1):
            mc = find_at(base_min + lvl)
            if mc is None:
                break
            if candle_win(mc, direction):
                mtg_used = lvl
                mtg_win = True
                break
    if mtg_win:
        return {"result": "WIN", "mtg_used": mtg_used, "checked": True, "payout": payout}
    return {"result": "LOSS", "mtg_used": mtg_used, "checked": True, "payout": payout}


@app.route("/future-check", methods=["POST"])
def future_check_route():
    data = request.get_json(silent=True) or {}
    signals = data.get("signals")
    if not isinstance(signals, list) or not signals:
        return jsonify({"success": False, "message": "signals array required"}), 400
    try:
        mtg_level = max(0, min(4, int(data.get("mtg_level", 0))))
    except Exception:
        mtg_level = 0
    try:
        payout_filter = float(data.get("payout_filter") or 0)
    except Exception:
        payout_filter = 0
    day = str(data.get("day") or "today").lower()
    now = datetime.now(UTC_PLUS_6)
    if day == "yesterday":
        now = now - timedelta(days=1)
    date_str = now.strftime("%Y-%m-%d")
    results = []
    for s in signals:
        pair = str(s.get("pair") or "").strip()
        if not pair:
            continue
        if not pair.endswith("_otc") and "otc" in pair.lower():
            pair = pair.replace("-OTC", "_otc").replace("-otc", "_otc")
        sig_time = str(s.get("time") or "")
        direction = str(s.get("direction") or "CALL").upper()
        display = str(s.get("display") or pair)
        closed, running = get_candles_with_running(pair, "1m", 500)
        r = _fc_check_one(list(closed), running, date_str, sig_time, direction, mtg_level)
        r["pair"] = pair
        r["display"] = display
        r["time"] = sig_time
        r["direction"] = direction
        results.append(r)
    wins = losses = ties = pending = skipped = 0
    for r in results:
        r["skipped"] = False
        if not r.get("checked"):
            pending += 1
        elif payout_filter > 0 and float(r.get("payout", 0) or 0) < payout_filter:
            r["skipped"] = True
            skipped += 1
        elif r["result"] == "WIN":
            wins += 1
        elif r["result"] == "LOSS":
            losses += 1
        elif r["result"] == "TIE":
            ties += 1
    total_decided = wins + losses
    accuracy = (wins / total_decided * 100.0) if total_decided else 0.0
    return jsonify({
        "success": True, "date": date_str, "mtg_level": mtg_level,
        "payout_filter": payout_filter, "total_checked": len(results),
        "wins": wins, "losses": losses, "ties": ties, "pending": pending,
        "skipped_low_payout": skipped, "accuracy": accuracy,
        "results": sorted(results, key=lambda x: x.get("time", ""))
    })


@sock.route('/ws')
def ws_channel(ws):
    """Fully WebSocket-based protected UI channel.

    curl / direct URL open korle kono UI source code paoa jabe na — asol UI sudhu
    ei socket-e explicit 'ui_request' pathalei server theke push hobe.
    """
    try:
        while True:
            raw = ws.receive(timeout=300)
            if raw is None:
                break
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            if isinstance(data, dict) and data.get('type') == 'ui_request':
                ws.send(json.dumps({'type': 'ui_html', 'html': UI_HTML}))
    except Exception:
        pass


@sock.route('/ws-ui')
def ws_ui_channel(ws):
    return ws_channel(ws)

# ==========================================
# FLASK API ROUTES (QUOTEX)
# ==========================================
@app.route('/markets', methods=['GET'])
def get_active_markets():
    return jsonify({
        "status": "success",
        "total_markets": len(ALL_INSTRUMENTS),
        "markets": ALL_INSTRUMENTS
    })

@app.route('/latest', methods=['GET'])
def get_latest_candle():
    """Lightweight real-time endpoint — last closed + LIVE running candle."""
    pair = request.args.get('Pair') or request.args.get('pair') or "USDPHP_otc"
    timeframe = request.args.get('Time') or request.args.get('time') or "1m"
    candles, running = get_candles_with_running(pair, timeframe, 5)
    if not candles and not running:
        return jsonify({"status": "error", "message": f"No data found for {pair}"}), 404
    return jsonify({
        "status": "success",
        "data": candles[0] if candles else running,
        "running": running,
        "closed": candles[:3] if candles else [],
        "feed": BOT_FEED_STATE.get("status", "unknown"),
        "live": bool(running),
    })

@app.route('/payout-history', methods=['GET'])
def get_payout_history():
    pair = request.args.get('Pair') or request.args.get('pair') or "USDPHP_otc"
    timeframe = request.args.get('Time') or request.args.get('time') or "1m"
    storage_key = f"{pair}_{timeframe}"
    if storage_key in PAYOUT_HISTORY:
        return jsonify({
            "status": "success",
            "pair": pair,
            "timeframe": timeframe,
            "payout_history": PAYOUT_HISTORY[storage_key]
        })
    return jsonify({"status": "error", "message": f"No history found for {pair}"}), 404

# ==========================================
# FLASK API ROUTES (AUTH & SETTINGS) — unchanged
# ==========================================
@app.route("/login", methods=["POST"])
def login_user():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    # Server-side password validation (timing-safe).
    # RavithXs → 3 free credits | F*ck_You → unlimited PRO
    password = str(password or "")
    pro_login = bool(PRO_ACCESS_PASSWORD) and hmac.compare_digest(password, PRO_ACCESS_PASSWORD)
    standard_login = hmac.compare_digest(password, APP_PASSWORD)
    if not (standard_login or pro_login):
        return jsonify({"success": False, "message": "Wrong password"}), 401

    # Auto-provision the shared app account on first unlock.
    # Entering the PRO key upgrades this account to permanent PRO/unlimited credits.
    users = load_users()
    email = SHARED_USER_EMAIL
    user = users.get(email)
    if not user:
        uid = generate_uid()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        user = {
            "name": "RAVITH",
            "email": email,
            "password": APP_PASSWORD,
            "uid": uid,
            "credit": DEFAULT_FREE_CREDITS,
            "credit_type": "pro" if pro_login else "free",
            "explicit_pro": bool(pro_login),
            "created_at": now,
            "last_login": now,
            "last_credit_reset": time.strftime("%Y-%m-%d"),
            "settings": dict(DEFAULT_SETTINGS)
        }
        users[email] = user

    if user.get("banned"):
        return jsonify({"success": False, "message": "Access blocked. Contact; @MAHBAUB_iX", "banned": True}), 403

    # Upgrade existing shared account when the PRO access key is used.
    # Do not downgrade an existing PRO account on standard-password login.
    if pro_login:
        user["credit_type"] = "pro"
        user["explicit_pro"] = True
        user["credit"] = "unlimited"

    if not user.get("uid"):
        user["uid"] = generate_uid()
    if not user.get("name"):
        user["name"] = "RAVITH"
    user["email"] = email

    today = time.strftime("%Y-%m-%d")
    if user.get("credit_type") != "pro" and user.get("last_credit_reset") != today:
        user["credit"] = DEFAULT_FREE_CREDITS
        user["last_credit_reset"] = today

    user["last_login"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if "settings" not in user or not isinstance(user["settings"], dict):
        user["settings"] = dict(DEFAULT_SETTINGS)

    save_users(users)
    session_token = issue_session(email)
    return jsonify({
        "success": True, "message": "Access granted",
        "name": user.get("name"), "uid": user.get("uid"),
        "credit": effective_credit_view(user)[0], "credit_type": effective_credit_view(user)[1],
        "email": email, "is_admin": bool(user.get("is_admin")),
        "admin_approved": bool(user.get("admin_approved")),
        "settings": user.get("settings"), "session": session_token
    })

@app.route("/profile", methods=["POST"])
def get_profile():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    users = load_users()
    user = users.get(email)
    if not user: return jsonify({"success": False, "message": "User not found"}), 404

    today = time.strftime("%Y-%m-%d")
    if user.get("credit_type") != "pro" and user.get("last_credit_reset") != today:
        user["credit"] = DEFAULT_FREE_CREDITS
        user["last_credit_reset"] = today
        save_users(users)

    return jsonify({
        "success": True, "name": user.get("name"), "email": email, "uid": user.get("uid"),
        "is_admin": bool(user.get("is_admin")), "admin_approved": bool(user.get("admin_approved")),
        "credit": effective_credit_view(user)[0], "credit_type": effective_credit_view(user)[1],
        "created_at": user.get("created_at"), "settings": user.get("settings")
    })

# ==========================================
# GLOBAL CONFIG (PUBLIC PRO mode etc.)
# ==========================================
GLOBAL_CONFIG_FILE = "global_config.json"

def load_global_config():
    try:
        with open(GLOBAL_CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            if isinstance(cfg, dict):
                cfg.setdefault("public_pro", False)
                return cfg
    except Exception:
        pass
    return {"public_pro": False}

def save_global_config(cfg):
    try:
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"⚠️ global config save error: {e}")

def is_pro_user(user):
    """PRO if: individually upgraded, OR PUBLIC PRO is ON and user was NOT explicitly pro-managed.

    explicit_pro=True  -> admin granted PRO directly (stays PRO even when PUBLIC PRO is OFF).
    explicit_pro=False -> admin set free credits / removed pro (never auto-promoted by PUBLIC PRO).
    """
    if not user:
        return False
    if user.get("credit_type") == "pro":
        return True
    try:
        if load_global_config().get("public_pro") and not user.get("explicit_pro"):
            return True
    except Exception:
        pass
    return False

def effective_credit_view(user):
    if is_pro_user(user):
        return "unlimited", "pro"
    return user.get("credit"), user.get("credit_type", "free")

@app.route("/use-credit", methods=["POST"])
def use_credit():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    users = load_users()
    user = users.get(email)

    if not user: return jsonify({"success": False, "message": "User not found"}), 404
    if is_pro_user(user):
        return jsonify({"success": True, "credit": "unlimited", "credit_type": "pro"})

    today = time.strftime("%Y-%m-%d")
    if user.get("last_credit_reset") != today:
        user["credit"] = DEFAULT_FREE_CREDITS
        user["last_credit_reset"] = today

    if user.get("credit", 0) <= 0:
        save_users(users)
        return jsonify({"success": False, "message": "No credits remaining.", "credit": 0, "credit_type": "free"}), 403

    user["credit"] -= 1
    save_users(users)
    return jsonify({"success": True, "credit": user["credit"], "credit_type": "free"})

@app.route("/save-settings", methods=["POST"])
def save_settings_route():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    settings = data.get("settings")

    if not email or not isinstance(settings, dict):
        return jsonify({"success": False, "message": "Email and settings object required"}), 400

    users = load_users()
    if email not in users: return jsonify({"success": False, "message": "User not found"}), 404

    existing = users[email].get("settings", dict(DEFAULT_SETTINGS))
    if not isinstance(existing, dict): existing = dict(DEFAULT_SETTINGS)
    existing.update(settings)
    
    users[email]["settings"] = existing
    users[email]["settings_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_users(users)
    return jsonify({"success": True, "message": "Settings saved"})

@app.route("/reset-results", methods=["POST"])
def reset_results_route():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    users = load_users()
    if not email or email not in users:
        return jsonify({"success": False, "message": "User not found"}), 404

    user = users[email]
    settings = user.get("settings", {})
    if not isinstance(settings, dict):
        settings = dict(DEFAULT_SETTINGS)

    settings["stats"] = {"wins": 0, "losses": 0, "streakW": 0, "streakL": 0}
    settings["tradeHistory"] = []
    _cs = str(settings.get("chartStyle", "Style 1 - Classic"))
    _cm = re.search(r"Style\s+(\d+)", _cs, re.I)
    _cn = int(_cm.group(1)) if _cm else 1
    settings["chartStyle"] = _cs if 1 <= _cn <= 26 else "Style 1 - Classic"
    settings["_v"] = SETTINGS_SCHEMA if "SETTINGS_SCHEMA" in globals() else 4
    settings["_updatedAt"] = int(time.time() * 1000)
    user["settings"] = settings
    user["settings_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_users(users)

    # Also clear persistent signal arrows.
    clear_signals(None)
    return jsonify({"success": True, "message": "Results reset", "settings": settings})

@app.route("/get-settings", methods=["POST"])
def get_settings_route():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    users = load_users()
    if email not in users: return jsonify({"success": False, "message": "User not found"}), 404
    return jsonify({"success": True, "settings": users[email].get("settings", dict(DEFAULT_SETTINGS))})

# ==========================================
# SIGNAL LOCK API (arrow storage — persistent until RESET)
# ==========================================
@app.route("/save-signal", methods=["POST"])
def save_signal_route():
    data = request.get_json(silent=True) or {}
    pair = str(data.get("pair", "")).strip()
    time_str = str(data.get("time", "")).strip()
    direction = str(data.get("direction", "")).strip().upper()
    if not pair or not time_str or direction not in ("BUY", "SELL", "CALL", "PUT"):
        return jsonify({"success": False, "message": "pair, time and direction required"}), 400
    register_signal(pair, time_str, direction)
    return jsonify({"success": True, "pair": pair, "time": time_str, "direction": direction,
                    "stored": len(SIGNAL_HISTORY.get(pair, {}))})

@app.route("/clear-signals", methods=["POST"])
def clear_signals_route():
    data = request.get_json(silent=True) or {}
    pair = str(data.get("pair", "")).strip()
    clear_signals(pair or None)
    return jsonify({"success": True, "cleared": pair or "ALL"})

# ==========================================
# ADMIN PANEL API (owner password protected)
# ==========================================
@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    _adm_email = str(data.get("email", "")).strip()
    _adm_users = load_users()
    _adm_u = _adm_users.get(_adm_email, {}) if _adm_email else {}
    _is_approved_admin = bool(_adm_u.get("is_admin")) and bool(_adm_u.get("admin_approved"))
    if str(data.get("password", "")) != ADMIN_PASSWORD and not _is_approved_admin:
        return jsonify({"success": False, "message": "Incorrect admin password"}), 401
    users = load_users()
    user_list = [{"email": e, "name": d.get("name"), "uid": d.get("uid"),
                  "credit": d.get("credit"), "credit_type": d.get("credit_type", "free"),
                  "banned": bool(d.get("banned")), "pinned": bool(d.get("pinned")),
                  "created_at": d.get("created_at"),
                  "last_login": d.get("last_login"), "is_admin": bool(d.get("is_admin")),
                  "admin_approved": bool(d.get("admin_approved"))} for e, d in users.items()]
    return jsonify({"success": True, "message": "Admin access granted", "total": len(user_list), "users": user_list})

@app.route("/block", methods=["GET", "POST"])
def block_user():
    data = request.get_json(silent=True) or {}
    uid = request.args.get("uid", "").strip() or str(data.get("uid", "")).strip()
    if not uid: return jsonify({"success": False, "message": "uid required"}), 400
    email, user = get_user_by_uid(uid)
    if not user: return jsonify({"success": False, "message": "User not found"}), 404
    users = load_users()
    users[email]["banned"] = True
    save_users(users)
    drop_sessions(email)  # invalidate every live session token of this account
    broadcast_ban(email, "Your account has been banned by the administrator.<br>Contact support: @MAHBAUB_iX")
    return jsonify({"success": True, "message": f"{email} has been BANNED 🚫", "email": email, "uid": uid, "banned": True})

@app.route("/unblock", methods=["GET", "POST"])
def unblock_user():
    data = request.get_json(silent=True) or {}
    uid = request.args.get("uid", "").strip() or str(data.get("uid", "")).strip()
    if not uid: return jsonify({"success": False, "message": "uid required"}), 400
    email, user = get_user_by_uid(uid)
    if not user: return jsonify({"success": False, "message": "User not found"}), 404
    users = load_users()
    users[email]["banned"] = False
    save_users(users)
    return jsonify({"success": True, "message": f"{email} has been UNBANNED ✅", "email": email, "uid": uid, "banned": False})

# ==========================================
# ADMIN ROUTES (unchanged)
# ==========================================
# ===== SERVER-SENT EVENTS — real-time BAN push to all open tabs/browsers of a user =====
@app.route("/events", methods=["GET"])
def events_stream():
    email = (request.args.get("email") or "").strip()
    q = queue.Queue(maxsize=16)
    if email:
        with BAN_SUB_LOCK:
            BAN_SUBSCRIBERS.setdefault(email, []).append(q)
        print(f"\U0001f514 [SSE] client subscribed: {email} (active: {len(BAN_SUBSCRIBERS.get(email, []))})")

    def stream():
        try:
            # instant state push: a banned account sees the popup even on a fresh page load
            if email:
                u = load_users().get(email)
                if not u:
                    yield 'event: account_deleted\ndata: {"message": "Your account is no longer registered on this server. You have been logged out."}\n\n'
                elif u.get("banned"):
                    yield 'event: ban\ndata: {"message": "Your account has been banned by the administrator.<br>Contact support: @MAHBAUB_iX"}\n\n'
            yield ": connected\n\n"
            while True:
                try:
                    ev = q.get(timeout=25)
                    if ev.get("type") == "ban":
                        yield "event: ban\ndata: " + json.dumps({"message": ev.get("message", "")}) + "\n\n"
                except queue.Empty:
                    yield ": ping\n\n"  # keep-alive
        except GeneratorExit:
            pass
        finally:
            with BAN_SUB_LOCK:
                try:
                    BAN_SUBSCRIBERS.get(email, []).remove(q)
                except Exception:
                    pass
            print(f"\U0001f515 [SSE] client disconnected: {email}")

    resp = Response(stream_with_context(stream()), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"] = "keep-alive"
    return resp

# ===== SESSION TERMINATION (ban popup OK -> server-side session drop) =====
@app.route("/session-logout", methods=["POST"])
def session_logout_route():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if email:
        drop_sessions(email)
        print(f"\U0001f512 [SESSION] all sessions terminated for {email}")
    return jsonify({"success": True})

# ===== REAL-TIME BAN STATUS (polled by the client; powers the glass ban popup) =====
@app.route("/ban-status", methods=["POST"])
def ban_status_route():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    users = load_users()
    user = users.get(email)
    if not user:
        drop_sessions(email)
        print(f"\U0001f512 [ACCOUNT] {email} missing from database -> session invalidated, client auto-logout")
        return jsonify({"success": True, "account_deleted": True,
                        "message": "Your account is no longer registered on this server.<br>You have been logged out automatically."})
    if user.get("banned"):
        return jsonify({"success": True, "banned": True,
                        "message": "Your account has been banned by the administrator.<br>Contact support: @MAHBAUB_iX"})
    return jsonify({"success": True, "banned": False})

# ===== ADMIN: PIN / UNPIN USER (pinned users stay on top of the admin list) =====
@app.route("/pin-user", methods=["GET", "POST"])
def pin_user_route():
    data = request.get_json(silent=True) or {}
    uid = request.args.get("uid", "").strip() or str(data.get("uid", "")).strip()
    if not uid:
        return jsonify({"success": False, "message": "uid required"}), 400
    email, user = get_user_by_uid(uid)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    users = load_users()
    new_state = not bool(users[email].get("pinned"))
    users[email]["pinned"] = new_state
    save_users(users)
    msg = f"{email} PINNED 📌" if new_state else f"{email} unpinned"
    return jsonify({"success": True, "message": msg, "email": email, "uid": uid, "pinned": new_state})

# ===== ADMIN: QUOTEX DATA-FEED LOGOUT / RELOGIN / STATUS =====
# LOGOUT: clears the collection account creds, drops the socket, stops data.
# RELOGIN: restores creds -> the background loop auto-reconnects & resumes data.
@app.route("/admin-quotex-logout", methods=["POST"])
def admin_quotex_logout_route():
    global q_instance
    # Disconnect the active data-feed socket immediately, while keeping the
    # configured credentials available for the next server startup.
    BOT_FEED_STATE["logged_in"] = False
    BOT_FEED_STATE["status"] = "disconnecting"
    q = q_instance
    q_instance = None
    if q is not None and AUTO_TRADE_LOOP is not None:
        async def _close_feed(client):
            try:
                await client.close()
            except Exception:
                pass
        try:
            asyncio.run_coroutine_threadsafe(_close_feed(q), AUTO_TRADE_LOOP)
        except Exception:
            pass
    BOT_FEED_STATE["status"] = "offline"
    print("🔌 [ADMIN] Quotex data-feed disconnected — live collection stopped")
    return jsonify({"success": True, "message": "Quotex data feed disconnected. Use RELOGIN with Gmail and password to reconnect."})

@app.route("/admin-quotex-relogin", methods=["POST"])
def admin_quotex_relogin_route():
    data = request.get_json(silent=True) or {}
    ssid_token = str(data.get("ssid_token") or data.get("token") or data.get("ssid") or "").strip()
    csrf_token = str(data.get("csrf_token") or data.get("csrf") or "").strip()
    if not ssid_token:
        return jsonify({"success": False, "message": "Quotex SSID / session token required."}), 400
    set_feed_session(ssid_token, csrf_token)
    BOT_FEED_STATE["logged_in"] = True
    BOT_FEED_STATE["status"] = "reconnecting"
    print("🔄 [ADMIN] Quotex data-feed RELOGIN requested with supplied token/CSRF...")
    return jsonify({"success": True, "message": "Relogin accepted. Reconnecting to the live Quotex data feed..."})


@app.route("/bot-status", methods=["GET"])
def bot_status_route():
    return jsonify({"success": True,
                    "online": bool(q_instance is not None and BOT_FEED_STATE.get("logged_in")),
                    "status": BOT_FEED_STATE.get("status", "unknown"),
                    "session": "token" if QUOTEX_SSID_TOKEN else "",
                    "has_csrf": bool(QUOTEX_CSRF_TOKEN),
                    "logged_in": bool(BOT_FEED_STATE.get("logged_in"))})


@app.route("/total-users", methods=["GET"])
def total_users():
    return jsonify({"success": True, "count": len(load_users()), "total": len(load_users())})

@app.route("/users", methods=["GET"])
def view_all_users():
    users = load_users()
    user_list = [{"email": e, "name": d.get("name"), "password": d.get("password"), "uid": d.get("uid"), "credit": d.get("credit"), "credit_type": d.get("credit_type", "free"), "created_at": d.get("created_at"), "last_login": d.get("last_login")} for e, d in users.items()]
    return jsonify({"success": True, "total": len(user_list), "users": user_list})

@app.route("/search-user", methods=["GET", "POST"])
def search_user():
    data = request.get_json(silent=True) or {}
    query = (request.args.get("q") or request.args.get("uid") or str(data.get("q", "") or data.get("uid", ""))).strip().lower()
    if not query:
        return jsonify({"success": False, "message": "Search query (uid / name / email) required"}), 400
    users = load_users()
    matches = []
    for e, d in users.items():
        if (query in str(d.get("uid", "")).lower()
                or query in str(d.get("name", "")).lower()
                or query in e.lower()):
            matches.append({"email": e, "name": d.get("name"), "uid": d.get("uid"),
                            "credit": d.get("credit"), "credit_type": d.get("credit_type", "free"),
                            "banned": bool(d.get("banned")), "created_at": d.get("created_at"),
                            "last_login": d.get("last_login")})
    if not matches:
        return jsonify({"success": False, "message": "No user found", "results": []}), 404
    return jsonify({"success": True, "count": len(matches), "results": matches})

@app.route("/admin-public-pro", methods=["GET", "POST"])
def admin_public_pro():
    data = request.get_json(silent=True) or {}
    password = str(data.get("password", "") or request.args.get("password", ""))
    if password != ADMIN_PASSWORD:
        return jsonify({"success": False, "message": "Incorrect admin password"}), 401
    cfg = load_global_config()
    if request.method == "POST":
        cfg["public_pro"] = bool(data.get("enabled"))
        save_global_config(cfg)
        print(f"👑 [ADMIN] PUBLIC PRO mode -> {'ON' if cfg['public_pro'] else 'OFF'}")
    return jsonify({"success": True, "public_pro": bool(cfg.get("public_pro"))})

def _admin_authorized(data=None):
    """True when the caller proves owner password OR is an approved admin account."""
    data = data or {}
    pw = str(data.get("password", "") or request.args.get("password", ""))
    if pw and pw == ADMIN_PASSWORD:
        return True
    caller = str(data.get("caller", "") or data.get("email", "") or request.args.get("caller", "")).strip()
    if caller:
        u = load_users().get(caller, {})
        if u and bool(u.get("is_admin")) and bool(u.get("admin_approved")):
            return True
    return False

def _apply_credit(uid, credit_val):
    email, user = get_user_by_uid(uid)
    if not user:
        return None, ({"success": False, "message": "User not found"}, 404)
    users = load_users()
    if str(credit_val).lower() == "pro":
        users[email].update({"credit_type": "pro", "credit": "unlimited", "explicit_pro": True})
        save_users(users)
        return {"success": True, "message": "Upgraded to PRO", "email": email, "uid": uid,
                "credit": "unlimited", "credit_type": "pro"}, None
    try:
        credit_num = int(credit_val)
        if credit_num < 0:
            raise ValueError()
    except Exception:
        return None, ({"success": False, "message": "Invalid credit value"}, 400)
    users[email].update({"credit_type": "free", "credit": credit_num, "explicit_pro": False})
    save_users(users)
    print(f"\U0001f4b0 [ADMIN] credit set -> uid={uid} email={email} credit={credit_num}")
    return {"success": True, "message": f"Credit set to {credit_num}", "email": email, "uid": uid,
            "name": users[email].get("name"), "credit": credit_num, "credit_type": "free"}, None

@app.route("/admin-set-credit", methods=["POST"])
def admin_set_credit():
    data = request.get_json(silent=True) or {}
    uid = str(data.get("uid", "")).strip()
    credit_val = data.get("credit", "")
    if not uid or credit_val in (None, ""):
        return jsonify({"success": False, "message": "uid and credit required"}), 400
    if not _admin_authorized(data):
        return jsonify({"success": False, "message": "Admin authorization failed (password or approved admin required)"}), 403
    ok, err = _apply_credit(uid, credit_val)
    if err:
        body, code = err
        return jsonify(body), code
    return jsonify(ok)

@app.route("/set-credit", methods=["GET", "POST"])
def set_credit():
    data = request.get_json(silent=True) or {}
    uid = (request.args.get("uid", "") or str(data.get("uid", ""))).strip()
    credit_val = (request.args.get("credit", "") or str(data.get("credit", ""))).strip()
    if not uid or not credit_val: return jsonify({"success": False, "message": "uid and credit required"}), 400
    # panel-based credit change (password / approved admin) -> use secure path
    if _admin_authorized(data):
        ok, err = _apply_credit(uid, credit_val)
        if err:
            body, code = err
            return jsonify(body), code
        return jsonify(ok)

    email, user = get_user_by_uid(uid)
    if not user: return jsonify({"success": False, "message": "User not found"}), 404

    users = load_users()
    if credit_val.lower() == "pro":
        users[email].update({"credit_type": "pro", "credit": "unlimited", "explicit_pro": True})
        save_users(users)
        return jsonify({"success": True, "message": "Upgraded to PRO", "email": email, "uid": uid, "credit": "unlimited", "credit_type": "pro"})
    else:
        try:
            credit_num = int(credit_val)
            users[email].update({"credit_type": "free", "credit": credit_num, "explicit_pro": False})
            save_users(users)
            return jsonify({"success": True, "message": f"Credit set to {credit_num}", "email": email, "uid": uid, "credit": credit_num, "credit_type": "free"})
        except:
            return jsonify({"success": False, "message": "Invalid credit value"}), 400

@app.route("/remove", methods=["GET"])
def remove_pro():
    uid = request.args.get("uid", "").strip()
    email, user = get_user_by_uid(uid)
    if not user: return jsonify({"success": False, "message": "User not found"}), 404

    users = load_users()
    users[email].update({"credit_type": "free", "credit": DEFAULT_FREE_CREDITS, "last_credit_reset": time.strftime("%Y-%m-%d"), "explicit_pro": False})
    save_users(users)
    return jsonify({"success": True, "message": "Downgraded to FREE", "email": email, "uid": uid, "credit": DEFAULT_FREE_CREDITS, "credit_type": "free"})


# ==========================================
# STATIC CHART IMAGE (unchanged)
# ==========================================
def draw_dashed_line(draw, start, end, color, width=1, dash_length=5):
    import math
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return
    dx /= length; dy /= length
    drawn = 0.0
    while drawn < length:
        seg = min(dash_length, length - drawn)
        draw.line([(x1 + dx * drawn, y1 + dy * drawn),
                   (x1 + dx * (drawn + seg), y1 + dy * (drawn + seg))], fill=color, width=width)
        drawn += dash_length * 2

def create_chart_image_api(pair, candles, signal_name="RAVITH-PRO"):
    if not candles or Image is None:
        return None
    candles = list(reversed(candles))  # chronological order for drawing

    WIDTH, HEIGHT = 900, 500
    BACKGROUND_COLOR = (10, 10, 20)
    GREEN = (0, 200, 0); RED = (255, 50, 50); BLUE = (0, 150, 255)
    YELLOW = (255, 255, 0); WHITE = (255, 255, 255); GRAY = (100, 100, 100)
    DARK_GRAY = (50, 50, 50); LIGHT_BLUE = (100, 200, 255); DARK_BLUE = (20, 20, 40)

    img = Image.new('RGB', (WIDTH, HEIGHT), color=BACKGROUND_COLOR)
    try:
        with urllib.request.urlopen(CHART_BACKGROUND_IMAGE_URL, timeout=5) as url:
            bg_img = Image.open(BytesIO(url.read())).convert("RGBA").resize((WIDTH, HEIGHT))
        bg_img.putdata([(p[0], p[1], p[2], 100) if p[3] > 0 else p for p in bg_img.getdata()])
        img = Image.alpha_composite(Image.new('RGBA', (WIDTH, HEIGHT), BACKGROUND_COLOR + (255,)), bg_img).convert('RGB')
    except Exception as e:
        print(f"bg image error: {e}")
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        font_large = font_medium = font_small = font_tiny = ImageFont.load_default()

    # --- Header ---
    header_y = 15
    title_text = f"{pair.replace('_otc', '-OTC').upper()} {signal_name} SIGNAL: "
    draw.text((20, header_y), title_text, fill=LIGHT_BLUE, font=font_large)
    title_w = draw.textlength(title_text, font=font_large)
    latest = candles[-1]
    latest_dir = "BUY" if latest['close'] > latest['open'] else "SELL"
    draw.text((20 + title_w, header_y), latest_dir, fill=GREEN if latest_dir == "BUY" else RED, font=font_large)
    count_text = f" | Candles: {len(candles)}"
    draw.text((20 + title_w + draw.textlength(latest_dir, font=font_large) + 10, header_y + 5),
              count_text, fill=YELLOW, font=font_medium)

    # --- BMA labels ---
    bma_y = 50
    x_pos = 20
    for t, c in zip(["BMA 9", "BMA 21", "BMA 30", "3IGNAL"], [YELLOW, BLUE, RED, GREEN]):
        draw.text((x_pos, bma_y), t, fill=c, font=font_medium)
        x_pos += draw.textlength(t, font=font_medium) + 20
    draw.text((x_pos, bma_y), "EMA: BULLISH", fill=GREEN, font=font_medium)

    all_prices = [c['high'] for c in candles] + [c['low'] for c in candles]
    min_price = min(all_prices) * 0.9998
    max_price = max(all_prices) * 1.0002
    price_range = max_price - min_price or max_price * 0.001

    CHART_AREA_LEFT, CHART_AREA_TOP, CHART_AREA_WIDTH, CHART_AREA_HEIGHT = 100, 80, 650, 350
    draw.rectangle([CHART_AREA_LEFT, CHART_AREA_TOP, CHART_AREA_LEFT + CHART_AREA_WIDTH,
                    CHART_AREA_TOP + CHART_AREA_HEIGHT], outline=DARK_GRAY, width=2)

    def sy(p):
        return CHART_AREA_TOP + CHART_AREA_HEIGHT - int((p - min_price) / price_range * CHART_AREA_HEIGHT)

    for i in range(5):
        y = CHART_AREA_TOP + int(i * CHART_AREA_HEIGHT / 4)
        draw.line([(CHART_AREA_LEFT, y), (CHART_AREA_LEFT + CHART_AREA_WIDTH, y)], fill=DARK_GRAY, width=1)

    ideal_w, ideal_sp = 10, 5
    n = len(candles)
    total_w = n * (ideal_w + ideal_sp) - ideal_sp
    if total_w > CHART_AREA_WIDTH:
        sf = CHART_AREA_WIDTH / total_w
        cw, sp = max(3, int(ideal_w * sf)), int(ideal_sp * sf)
    else:
        cw, sp = ideal_w, ideal_sp
    start_x = CHART_AREA_LEFT + cw // 2

    for i, candle in enumerate(candles):
        xc = start_x + i * (cw + sp)
        if xc > CHART_AREA_LEFT + CHART_AREA_WIDTH:
            break
        xl, xr = xc - cw // 2, xc + cw // 2
        yh, yl = sy(candle['high']), sy(candle['low'])
        draw.line([(xc, yh), (xc, yl)], fill=WHITE, width=1)
        bull = candle['close'] > candle['open']
        bc = GREEN if bull else RED
        yo, yc = sy(candle['open']), sy(candle['close'])
        yt, yb = min(yo, yc), max(yo, yc)
        yb = max(yb, yt + 2)
        draw.rectangle([xl + 1, yt, xr - 1, yb], fill=bc, outline=bc)
        draw.rectangle([xl, yt, xr, yb], outline=bc, width=1)

    # --- Current price dashed line ---
    lp = latest['close']
    yp = sy(lp)
    draw_dashed_line(draw, (CHART_AREA_LEFT, yp), (CHART_AREA_LEFT + CHART_AREA_WIDTH, yp), YELLOW, 2, 8)
    draw.rectangle([CHART_AREA_LEFT + CHART_AREA_WIDTH - 60, yp - 10,
                    CHART_AREA_LEFT + CHART_AREA_WIDTH, yp + 10], fill=YELLOW)
    draw.text((CHART_AREA_LEFT + CHART_AREA_WIDTH - 55, yp - 7), f"{lp:.4f}", fill=(0, 0, 0), font=font_tiny)

    # --- Right info panel ---
    ix, iy = CHART_AREA_LEFT + CHART_AREA_WIDTH + 20, CHART_AREA_TOP
    draw.rectangle([ix - 10, iy - 10, WIDTH - 20, iy + 250], fill=DARK_BLUE, outline=GRAY)
    draw.text((ix, iy), "BULLTERMINAL", fill=GREEN, font=font_medium)
    draw.text((ix, iy + 25), "PRICE TERMINAL", fill=BLUE, font=font_medium)
    closes = [c['close'] for c in candles]
    sma9 = sum(closes[-9:]) / min(9, len(closes))
    sma21 = sum(closes[-21:]) / min(21, len(closes))
    sma30 = sum(closes[-30:]) / min(30, len(closes))
    sig = latest.get('signal') or ('CALL' if latest['close'] > latest['open'] else 'PUT')
    info = [
        (f"SMA 9: {sma9:.4f}", GREEN if sma9 > lp else RED),
        (f"SMA 21: {sma21:.4f}", GREEN if sma21 > lp else RED),
        (f"SMA 30: {sma30:.4f}", GREEN if sma30 > lp else RED),
        (f"Current: {lp:.4f}", GREEN if sig == "CALL" else RED),
        (f"High: {latest['high']:.4f}", GREEN),
        (f"Low: {latest['low']:.4f}", RED),
        (f"Open: {latest['open']:.4f}", GRAY),
        (f"Signal: {sig}", GREEN if sig == "CALL" else RED),
    ]
    for i, (t, c) in enumerate(info):
        draw.text((ix, iy + 55 + i * 20), t, fill=c, font=font_small)
    draw.line([(ix, iy + 210), (WIDTH - 30, iy + 210)], fill=GRAY, width=1)
    draw.text((ix, iy + 220), f"BULLTERMINAL + {len(candles)} CANDLES", fill=GREEN, font=font_medium)

    # --- Bottom status bar ---
    by = HEIGHT - 40
    draw.rectangle([10, by - 5, WIDTH - 10, by + 30], fill=DARK_BLUE, outline=GRAY)
    tstr = (latest.get('time') or '')[11:] or "00:00:00"
    draw.text((20, by), f"TIME: {tstr}", fill=WHITE, font=font_small)
    draw.text((200, by), f"OPEN: {latest['open']:.5f}", fill=GRAY, font=font_small)
    draw.text((350, by), f"CLOSE: {latest['close']:.5f}", fill=GREEN if sig == "CALL" else RED, font=font_small)
    draw.text((500, by), f"HIGH: {latest['high']:.5f}", fill=GREEN, font=font_small)
    draw.text((650, by), f"LOW: {latest['low']:.5f}", fill=RED, font=font_small)
    sbx = WIDTH - 120
    sc = GREEN if sig == "CALL" else RED
    draw.rectangle([sbx, by, sbx + 100, by + 25], fill=sc, outline=WHITE)
    st = f"SIGNAL: {sig}"
    draw.text((sbx + (100 - draw.textlength(st, font=font_medium)) // 2, by + 3), st, fill=(0, 0, 0), font=font_medium)

    draw.rectangle([5, 5, WIDTH - 5, HEIGHT - 5], outline=GRAY, width=2)
    img = img.resize((WIDTH * 2, HEIGHT * 2), Image.LANCZOS)   # HQ 2x output
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

@app.route('/chart_image', methods=['GET'])
def chart_image_handler():
    pair = request.args.get("Pair") or request.args.get("pair")
    ss_name = request.args.get("SS", "RAVITH-PRO")
    timeframe = request.args.get("Time") or request.args.get("time") or "1m"
    candle_param = request.args.get("Candle")
    candle_count = 60
    if candle_param:
        try:
            candle_count = int(candle_param)
            if candle_count < 1 or candle_count > 500:
                return jsonify({"error": "Candle count must be 1-500"}), 400
        except ValueError:
            return jsonify({"error": "Candle count must be a number"}), 400
    if not pair:
        return jsonify({"error": "Use: ?Pair=USDPHP_otc"}), 400
    if Image is None:
        return jsonify({"error": "Pillow not installed on server (pip install pillow)"}), 500
    candles, running = get_candles_with_running(pair, timeframe, candle_count)
    if not candles:
        return jsonify({"error": f"No data for {pair}"}), 404
    try:
        buf = create_chart_image_api(pair, candles, ss_name)
        if buf:
            return send_file(buf, mimetype='image/png')
        return jsonify({"error": "Chart generation failed"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



# ==========================================
# QUOTEX AUTO-TRADE ENGINE (per user account)
# Settings -> Quotex Gmail + password login, Demo/Real
# select, per-trade amount, TP/SL, MTG 2x steps.
# ==========================================
AUTO_TRADE_LOOP = None
QUOTEX_AUTO_LOCK = threading.Lock()
QUOTEX_AUTO_STATE = {}  # email -> account dict


# ============================================================================
# LIVE-CANDLE TRIGGER HELPERS (THE ONLY SOURCE OF TRUTH FOR ENTRY TIMING)
# ----------------------------------------------------------------------------
# The Auto Trade engine NEVER uses datetime.now() / server clock / UTC math to
# decide WHEN to place a trade. It only compares candle identifiers coming from
# the SAME live market-data source (RUNNING_CANDLES — fed by the real Quotex
# tick websocket). Comparison is done on pure UNIX candle-start identifiers,
# which makes the whole entry decision timezone-independent by design.
# ============================================================================
def _candle_start_key(time_str):
    """Convert a candle identifier string ("YYYY-MM-DD HH:MM:SS") to its pure
    minute-start UNIX key. This is ONLY an identifier for equality/ordering
    checks between candles of the SAME live source — never a scheduling clock."""
    try:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})", str(time_str or ""))
        if not m:
            return None
        y, mo, d, h, mi, s = (int(x) for x in m.groups())
        return int(datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc).timestamp())
    except Exception:
        return None


def _live_candle_key(pair):
    """Candle-start identifier of the CURRENT RUNNING candle on the live chart
    data stream (RUNNING_CANDLES comes straight from the Quotex tick socket)."""
    rc = RUNNING_CANDLES.get(pair, {}).get("1m")
    if rc and isinstance(rc.get("start"), (int, float)):
        return int(rc["start"])
    return None


def _live_candle_info(pair):
    """Full live snapshot: running candle key + display time (chart-derived)."""
    rc = RUNNING_CANDLES.get(pair, {}).get("1m")
    if not rc:
        return None, None
    key = int(rc["start"]) if isinstance(rc.get("start"), (int, float)) else None
    dt = ts_to_dt(rc.get("start"))
    tstr = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None
    return key, tstr


async def _live_candle_wait_for(trade, pair, target_time, poll=0.25, max_grace_sec=180):
    """LIVE-CANDLE WAIT — block until the LIVE CHART actually reaches the target
    candle start, then return "entered" so the caller can fire client.buy() NOW.

    - Polls the running-candle engine (real tick stream), NOT datetime.now().
    - If the target candle is ALREADY the live running candle -> enter instantly.
    - If the live candle has moved PAST the target -> return "missed" (no late trade).
    - If live data is briefly unavailable -> keep the target unchanged & retry.
    - Only after the target has been missed for longer than max_grace_sec (live
      data completely dead) do we give up — we NEVER fall back to a local timer.
    """
    target_key = _candle_start_key(target_time)
    if target_key is None:
        return "no-target"
    ticks_seen = 0
    # Stall guard: time.monotonic() is used ONLY to detect a dead tick stream
    # (feed stopped / admin logout) — it NEVER participates in entry timing.
    last_seen_key = None
    last_change = time.monotonic()
    while True:
        if trade.get("cancelled"):
            return "cancelled"
        live_key, _live_t = _live_candle_info(pair)
        if live_key is None:
            # Live tick stream has not delivered a candle yet — retry shortly.
            # IMPORTANT: we do NOT place the trade from a local clock fallback.
            if time.monotonic() - last_change > max_grace_sec:
                return "stalled"                   # feed dead too long — abort safely
            await asyncio.sleep(0.5)
            continue
        if live_key != last_seen_key:
            last_seen_key = live_key
            last_change = time.monotonic()         # live candle advanced — stream is alive
        elif time.monotonic() - last_change > max_grace_sec:
            return "stalled"                       # same candle frozen for 3 min — feed dead
        if live_key == target_key:
            return "entered"                       # 🎯 target candle just STARTED live
        if live_key > target_key:
            return "missed"                        # live candle moved past target — no late order
        ticks_seen += 1                            # live_key < target_key: still the candle before target
        await asyncio.sleep(poll)


def _auto_new_account():
    return {
        "client": None, "connected": False,
        "account_type": "demo", "balance": 0.0,
        "qx_email": "", "qx_password": "",
        "settings": {"enabled": False, "trade_amount": 2.0, "take_profit": 10.0,
                     "stop_loss": 20.0, "mtg_steps": 0, "account_type": "demo"},
        "session": {"pnl": 0.0, "trades": 0, "wins": 0, "losses": 0},
        "trade": None, "last_result": None,
    }


def _auto_get(email):
    with QUOTEX_AUTO_LOCK:
        if email not in QUOTEX_AUTO_STATE:
            QUOTEX_AUTO_STATE[email] = _auto_new_account()
        return QUOTEX_AUTO_STATE[email]


def _auto_update_settings(acc, s):
    if not isinstance(s, dict):
        return
    st = acc["settings"]
    try:
        if "enabled" in s: st["enabled"] = bool(s["enabled"])
        if "trade_amount" in s: st["trade_amount"] = max(1.0, float(s["trade_amount"]))
        if "take_profit" in s: st["take_profit"] = float(s["take_profit"])
        if "stop_loss" in s: st["stop_loss"] = abs(float(s["stop_loss"]))
        if "mtg_steps" in s: st["mtg_steps"] = max(0, min(3, int(s["mtg_steps"])))
        if s.get("account_type") in ("demo", "real"): st["account_type"] = s["account_type"]
    except Exception:
        pass


def _auto_stop_limits_hit(acc):
    pnl = acc["session"]["pnl"]
    if acc["settings"]["take_profit"] > 0 and pnl >= acc["settings"]["take_profit"]:
        return "TP"
    if acc["settings"]["stop_loss"] > 0 and pnl <= -abs(acc["settings"]["stop_loss"]):
        return "SL"
    return None


def _auto_status_dict(acc):
    d = {"success": True, "connected": bool(acc["connected"]),
         "account_type": acc["account_type"], "balance": acc["balance"],
         "session": dict(acc["session"]), "settings": dict(acc["settings"]),
         "last_result": acc.get("last_result")}
    if acc["trade"]:
        d["trade"] = {k: acc["trade"].get(k) for k in
                      ("pair", "direction", "amount", "pending", "target_time", "mtg_level")}
    return d


async def _auto_trade_cycle(email, pair, direction, target_time, payout, mtg_level, amount):
    """LIVE-CANDLE ENTRY ARCHITECTURE (initial trade & every MTG step use this):

        signal running candle + 2 minutes  =  TARGET CANDLE (candle identifier ONLY)
                     ↓
        poll LIVE tick stream (RUNNING_CANDLES) every 0.25s
                     ↓
        live running candle BECOMES the target candle
                     ↓
        IMMEDIATELY client.buy(amount, pair, direction, 1)

    ❌ NO datetime.now() scheduling   ❌ NO UTC/server-time conversion
    ❌ NO fixed sleep timer for entry ❌ NO timezone arithmetic
    ✅ Entry is triggered ONLY by the live market candle reaching the target."""
    acc = _auto_get(email)
    trade = acc["trade"]
    client = acc["client"]
    try:
        # ---- PHASE 1: wait for the LIVE CHART to reach the target candle ----
        trade["pending"] = True
        wait_result = await _live_candle_wait_for(trade, pair, target_time)
        trade["pending"] = False

        if wait_result == "cancelled":
            return
        if wait_result == "missed":
            # Target candle already passed on the live chart — DO NOT place a late trade.
            acc["last_result"] = "MISSED"
            print(f"⏭️ auto-trade [{email}] target candle {target_time} already passed on live chart — trade skipped safely")
            return
        if wait_result == "stalled":
            # Live data stream went dead before the target candle could be confirmed.
            # We NEVER fall back to server time — the order is simply not placed.
            acc["last_result"] = "FEED-DEAD"
            print(f"📡 auto-trade [{email}] live feed stalled before target {target_time} — order NOT placed (no clock fallback)")
            return
        if wait_result != "entered":
            acc["last_result"] = "NO-TARGET"
            print(f"⚠️ auto-trade [{email}] invalid target candle reference '{target_time}' — skipped")
            return
        if not acc["connected"] or client is None:
            return

        # ---- PHASE 2: duplicate-order protection — the same target candle can
        # never fire two orders, and a busy account never opens a second trade ----
        if trade.get("entry_triggered"):
            print(f"🛡️ auto-trade [{email}] duplicate entry blocked for candle {target_time}")
            return
        trade["entry_triggered"] = True   # lock BEFORE buy — one candle = one order
        try:
            bal = await client.get_balance()
            if isinstance(bal, (int, float)):
                acc["balance"] = float(bal)
                if acc["balance"] < amount:
                    print(f"⚠️ auto-trade [{email}] insufficient balance for ${amount}")
                    return
        except Exception:
            pass
        status, info = False, {}
        try:
            status, info = await client.buy(amount, pair, direction, 1)
        except Exception as e:
            print(f"⚠️ auto-trade buy error [{email}]: {e}")
        if not status:
            print(f"⚠️ auto-trade [{email}] order rejected for {pair}")
            return
        order_id = info.get("id") if isinstance(info, dict) else None
        print(f"🎯 auto-trade [{email}] {pair} {direction.upper()} ${amount} placed (MTG{mtg_level})")
        await asyncio.sleep(65)
        win = None
        if order_id:
            try:
                win = await client.check_win(order_id)
            except Exception:
                win = None
        try:
            new_bal = await client.get_balance()
            if isinstance(new_bal, (int, float)):
                acc["balance"] = float(new_bal)
        except Exception:
            pass
        ses = acc["session"]
        ses["trades"] += 1
        if win is True:
            profit = round(amount * (float(payout) if payout else 80.0) / 100.0, 2)
            ses["pnl"] = round(ses["pnl"] + profit, 2)
            ses["wins"] += 1
            acc["last_result"] = "WIN"
            print(f"✅ auto-trade [{email}] WIN +${profit} (session PnL ${ses['pnl']})")
        elif win is False:
            ses["pnl"] = round(ses["pnl"] - amount, 2)
            ses["losses"] += 1
            acc["last_result"] = "LOSS"
            print(f"❌ auto-trade [{email}] LOSS -${amount} (session PnL ${ses['pnl']})")
        else:
            acc["last_result"] = "UNKNOWN"
            print(f"⚠️ auto-trade [{email}] result unknown for order {order_id}")
        hit = _auto_stop_limits_hit(acc)
        if hit:
            print(f"🛑 auto-trade [{email}] {hit} hit — auto trade stopped (PnL ${ses['pnl']})")
            acc["settings"]["enabled"] = False
    except Exception as e:
        print(f"⚠️ auto-trade cycle error [{email}]: {e}")
        traceback.print_exc()
    finally:
        acc["trade"] = None


def _auto_launch(email, pair, direction, target_time, payout, mtg_level, amount):
    acc = _auto_get(email)
    if AUTO_TRADE_LOOP is None:
        return False
    acc["trade"] = {"pair": pair, "direction": direction, "amount": amount,
                    "target_time": target_time, "payout": payout, "mtg_level": mtg_level,
                    "pending": True, "cancelled": False, "entry_triggered": False}
    asyncio.run_coroutine_threadsafe(
        _auto_trade_cycle(email, pair, direction, target_time, payout, mtg_level, amount),
        AUTO_TRADE_LOOP)
    return True


@app.route("/quotex-login", methods=["POST"])
def quotex_login_route():
    """Login with Quotex web session tokens only: SSID (token) + CSRF (XSRF-TOKEN)."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip() or "default"
    ssid_token = str(data.get("ssid_token") or data.get("token") or data.get("ssid") or "").strip()
    csrf_token = str(data.get("csrf_token") or data.get("csrf") or "").strip()
    account_type = str(data.get("account_type", "demo")).lower()
    if account_type not in ("demo", "real"):
        account_type = "demo"
    if not ssid_token:
        return jsonify({"success": False, "message": "Quotex SSID / session token required"}), 400

    acc = _auto_get(email)
    _auto_update_settings(acc, data.get("settings"))
    acc["settings"]["account_type"] = account_type
    set_feed_session(ssid_token, csrf_token)
    acc["account_type"] = account_type
    acc["qx_email"] = "token-session"
    acc["qx_password"] = ""

    async def _do_connect():
        client = build_quotex_client()
        try:
            success, reason = await asyncio.wait_for(client.connect(), timeout=45)
        except Exception as e:
            return None, str(e)
        if not success:
            return None, str(reason)
        try:
            await client.change_account("PRACTICE" if account_type == "demo" else "REAL")
        except Exception:
            pass
        bal = 0.0
        try:
            bal = await client.get_balance()
        except Exception:
            pass
        return client, bal

    if AUTO_TRADE_LOOP is None:
        return jsonify({"success": True, "connected": False, "pending": True,
                        "message": "Token/CSRF accepted. Feed engine starting, retry shortly."}), 200
    try:
        future = asyncio.run_coroutine_threadsafe(_do_connect(), AUTO_TRADE_LOOP)
        client, bal = future.result(timeout=60)
    except Exception as e:
        return jsonify({"success": False, "message": f"Connection error: {e}"}), 200
    if client is None:
        return jsonify({"success": False, "message": f"Login failed: {bal}"}), 200

    acc["client"] = client
    acc["connected"] = True
    acc["balance"] = float(bal) if isinstance(bal, (int, float)) else 0.0
    acc["session"] = {"pnl": 0.0, "trades": 0, "wins": 0, "losses": 0}
    print(f"✅ Quotex session connected [{email}] {account_type.upper()} bal={acc['balance']}")
    return jsonify({"success": True, "connected": True,
                    "account_type": account_type, "balance": acc["balance"]})


@app.route("/quotex-disconnect", methods=["POST"])
def quotex_disconnect_route():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip() or "default"
    acc = _auto_get(email)
    acc["connected"] = False
    acc["settings"]["enabled"] = False
    if acc["trade"]:
        acc["trade"]["cancelled"] = True
        acc["trade"] = None
    client = acc.get("client")
    acc["client"] = None
    if client is not None and AUTO_TRADE_LOOP is not None:
        async def _close(c):
            try:
                await c.close()
            except Exception:
                pass
        try:
            asyncio.run_coroutine_threadsafe(_close(client), AUTO_TRADE_LOOP)
        except Exception:
            pass
    return jsonify({"success": True, "message": "Disconnected"})


@app.route("/quotex-status", methods=["POST"])
def quotex_status_route():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip() or "default"
    acc = _auto_get(email)
    _auto_update_settings(acc, data.get("settings"))
    return jsonify(_auto_status_dict(acc))


@app.route("/auto-trade", methods=["POST"])
def auto_trade_route():
    """Queue auto trade for a generated signal (signal er market + time e trade)."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip() or "default"
    pair = (data.get("pair") or "").replace("-OTC", "_otc")
    time_str = data.get("time") or ""
    direction = str(data.get("direction") or "").upper()
    payout = data.get("payout") or 0
    acc = _auto_get(email)
    _auto_update_settings(acc, data.get("settings"))

    if not acc["settings"]["enabled"]:
        return jsonify({"success": True, "queued": False, "reason": "disabled",
                        "message": "Auto trade is OFF in Settings"})
    if not acc["connected"] or acc["client"] is None:
        return jsonify({"success": False, "queued": False, "reason": "offline",
                        "message": "Quotex not connected — login from Settings first"})
    if acc["trade"] is not None:
        return jsonify({"success": False, "queued": False, "reason": "busy",
                        "message": "A trade is already running"})
    if _auto_stop_limits_hit(acc):
        acc["settings"]["enabled"] = False
        return jsonify({"success": False, "queued": False, "reason": "limit",
                        "message": "TP/SL hit — auto trade stopped"})
    if direction not in ("BUY", "SELL"):
        return jsonify({"success": False, "queued": False, "reason": "bad-direction",
                        "message": "Invalid direction"})
    amount = round(float(acc["settings"]["trade_amount"]), 2)
    ok = _auto_launch(email, pair, "call" if direction == "BUY" else "put",
                      time_str, payout, 0, amount)
    if not ok:
        return jsonify({"success": False, "queued": False, "message": "Engine loop not ready"}), 503
    hhmm = time_str[11:16] if len(time_str) >= 16 else time_str
    print(f"📥 auto-trade queued [{email}] {pair} {direction} ${amount} @ {hhmm}")
    return jsonify({"success": True, "queued": True, "pair": pair,
                    "direction": direction, "amount": amount, "entry": hhmm})


@app.route("/auto-trade/decision", methods=["POST"])
def auto_trade_decision_route():
    """MTG decision after direct loss. MTG 2x rule: base * 2^step ($2 -> MTG1 $4 -> MTG2 $8)."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip() or "default"
    pair = (data.get("pair") or "").replace("-OTC", "_otc")
    direction = str(data.get("direction") or "").upper()
    target_time = data.get("target_time") or ""
    payout = data.get("payout") or 0
    acc = _auto_get(email)

    if not acc["settings"]["enabled"]:
        return jsonify({"success": True, "place": False, "reason": "disabled"})
    if not acc["connected"] or acc["client"] is None:
        return jsonify({"success": True, "place": False, "reason": "offline"})
    if acc["trade"] is not None:
        return jsonify({"success": True, "place": False, "reason": "busy"})
    hit = _auto_stop_limits_hit(acc)
    if hit:
        acc["settings"]["enabled"] = False
        return jsonify({"success": True, "place": False, "reason": hit})
    try:
        mtg_level = int(data.get("mtg_level", 1))
    except Exception:
        mtg_level = 1
    mtg_level = max(1, min(10, mtg_level))
    if mtg_level > int(acc["settings"].get("mtg_steps", 0)):
        return jsonify({"success": True, "place": False, "reason": "mtg-max"})
    amount = round(float(acc["settings"]["trade_amount"]) * (2 ** mtg_level), 2)
    if acc["balance"] and amount > float(acc["balance"]):
        return jsonify({"success": True, "place": False, "reason": "insufficient-balance"})
    if direction not in ("BUY", "SELL"):
        return jsonify({"success": True, "place": False, "reason": "bad-direction"})
    ok = _auto_launch(email, pair, "call" if direction == "BUY" else "put",
                      target_time, payout, mtg_level, amount)
    if not ok:
        return jsonify({"success": True, "place": False, "reason": "engine-not-ready"})
    return jsonify({"success": True, "place": True, "amount": amount, "mtg_level": mtg_level})


@app.route("/auto-trade/cancel", methods=["POST"])
def auto_trade_cancel_route():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip() or "default"
    acc = _auto_get(email)
    cancelled = False
    if acc["trade"] and acc["trade"].get("pending"):
        acc["trade"]["cancelled"] = True
        acc["trade"] = None
        cancelled = True
    return jsonify({"success": True, "cancelled": cancelled})


# ==========================================
# UPGRADE PACK v2 — WIN/LOSS PERSISTENCE, ADMIN MANAGEMENT
# ==========================================
@app.route("/record-result", methods=["POST"])
def record_result_route():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    result = str(data.get("result", "")).strip().upper()
    if not email or result not in ("WIN", "LOSS"):
        return jsonify({"success": False, "message": "email and result (WIN/LOSS) required"}), 400
    users = load_users()
    if email not in users:
        return jsonify({"success": False, "message": "User not found"}), 404
    u = users[email]
    s = u.get("settings")
    if not isinstance(s, dict):
        s = dict(DEFAULT_SETTINGS)
    stats = s.get("stats")
    if not isinstance(stats, dict):
        stats = {"wins": 0, "losses": 0, "streakW": 0, "streakL": 0}
    if result == "WIN":
        stats["wins"] = int(stats.get("wins", 0)) + 1
        stats["streakW"] = int(stats.get("streakW", 0)) + 1
        stats["streakL"] = 0
    else:
        stats["losses"] = int(stats.get("losses", 0)) + 1
        stats["streakL"] = int(stats.get("streakL", 0)) + 1
        stats["streakW"] = 0
    s["stats"] = stats
    hist = s.get("tradeHistory")
    if not isinstance(hist, list):
        hist = []
    hist.append({"result": result, "pair": str(data.get("pair", "")),
                 "direction": str(data.get("direction", "")),
                 "amount": data.get("amount", 0),
                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    s["tradeHistory"] = hist[-500:]
    u["settings"] = s
    u["settings_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_users(users)
    return jsonify({"success": True, "stats": stats, "total_trades": len(hist)})

@app.route("/trade-history", methods=["POST"])
def trade_history_route():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    users = load_users()
    if email not in users:
        return jsonify({"success": False, "message": "User not found"}), 404
    s = users[email].get("settings", {}) or {}
    return jsonify({"success": True,
                    "stats": s.get("stats", {"wins": 0, "losses": 0, "streakW": 0, "streakL": 0}),
                    "history": (s.get("tradeHistory") or [])[-100:]})

@app.route("/admin-check", methods=["POST"])
def admin_check_route():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    users = load_users()
    u = users.get(email, {})
    ok = bool(u.get("is_admin")) and bool(u.get("admin_approved"))
    return jsonify({"success": True, "is_admin": ok})

def _rv_owner_ok(data):
    return str(data.get("password", "")) == ADMIN_PASSWORD

def _rv_admin_ok(data):
    email = str(data.get("caller", "")).strip()
    if not email:
        return False
    users = load_users()
    u = users.get(email, {})
    return bool(u.get("is_admin")) and bool(u.get("admin_approved"))

def _rv_may_manage(data):
    return _rv_owner_ok(data) or _rv_admin_ok(data)

@app.route("/admin-add", methods=["POST"])
def admin_add_route():
    data = request.get_json(silent=True) or {}
    if not _rv_may_manage(data):
        return jsonify({"success": False, "message": "Owner password required"}), 403
    target = str(data.get("email", "") or data.get("uid", "")).strip()
    users = load_users()
    email = target if target in users else None
    if email is None:
        for e, d in users.items():
            if str(d.get("uid", "")) == target:
                email = e
                break
    if email is None:
        return jsonify({"success": False, "message": "User not found"}), 404
    users[email]["is_admin"] = True
    users[email]["admin_approved"] = True
    save_users(users)
    return jsonify({"success": True, "message": email + " is now an approved ADMIN",
                    "email": email, "name": users[email].get("name")})

@app.route("/admin-remove", methods=["POST"])
def admin_remove_route():
    data = request.get_json(silent=True) or {}
    if not _rv_may_manage(data):
        return jsonify({"success": False, "message": "Owner password required"}), 403
    target = str(data.get("email", "") or data.get("uid", "")).strip()
    users = load_users()
    email = target if target in users else None
    if email is None:
        for e, d in users.items():
            if str(d.get("uid", "")) == target:
                email = e
                break
    if email is None:
        return jsonify({"success": False, "message": "User not found"}), 404
    users[email]["is_admin"] = False
    users[email]["admin_approved"] = False
    save_users(users)
    return jsonify({"success": True, "message": email + " removed from ADMIN", "email": email})

@app.route("/admin-list", methods=["POST"])
def admin_list_route():
    data = request.get_json(silent=True) or {}
    if not _rv_may_manage(data):
        return jsonify({"success": False, "message": "Owner password required"}), 403
    users = load_users()
    admins = [{"email": e, "name": d.get("name"), "uid": d.get("uid"),
               "approved": bool(d.get("admin_approved"))}
              for e, d in users.items() if d.get("is_admin")]
    return jsonify({"success": True, "admins": admins, "total": len(admins)})

# ==========================================
# MAIN EXECUTION
# ==========================================
# ==========================================================
#  TELEGRAM CONTROL BOT  —  only BOT_TOKEN variable is needed
#  Bot start -> /start -> SSID Token -> CSRF -> Quotex live feed login
#  No ADMIN_ID / OWNER_ID / PAIR CODE needed anywhere.
# ==========================================================
import contextlib
import subprocess
import atexit
import signal as _signal

import requests as _requests


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    os.replace(tmp, path)


class QuickTunnel:
    """Cloudflare Quick Tunnel (public URL for the Flask UI)."""

    def __init__(self, port):
        self.port = port
        self.process = None
        self.url = None
        self.ready = threading.Event()
        self.lock = threading.Lock()

    def _read(self, proc):
        try:
            for line in proc.stdout:
                match = re.search(r"https://[a-zA-Z0-9-]+[.]trycloudflare[.]com", line)
                if match and self.process is proc:
                    self.url = match.group(0)
                    self.ready.set()
        finally:
            if self.process is proc:
                self.url = None
                self.ready.set()

    def start(self, timeout=50):
        with self.lock:
            if self.process and self.process.poll() is None and self.url:
                return self.url
            self._stop_locked()
            self.ready.clear()
            binary = os.getenv("CLOUDFLARED_BIN", "cloudflared")
            try:
                self.process = subprocess.Popen(
                    [binary, "tunnel", "--no-autoupdate", "--protocol", "http2",
                     "--url", "http://127.0.0.1:" + str(self.port)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            except FileNotFoundError:
                raise RuntimeError(
                    "cloudflared installed nei. Dockerfile/railway image e cloudflared add korun, "
                    "othoba PORT er public URL directly use korun.")
            threading.Thread(target=self._read, args=(self.process,), daemon=True).start()
            if self.ready.wait(timeout) and self.url and self.process.poll() is None:
                return self.url
            self._stop_locked()
            raise RuntimeError("Cloudflare URL pai ni; abar /server din.")

    def _stop_locked(self):
        proc, self.process = self.process, None
        self.url = None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def stop(self):
        with self.lock:
            self._stop_locked()


def feed_login(ssid, csrf):
    """Store the manual session token and let the async feed worker connect."""
    global QUOTEX_SSID_TOKEN, QUOTEX_CSRF_TOKEN
    QUOTEX_SSID_TOKEN = (ssid or "").strip()
    QUOTEX_CSRF_TOKEN = (csrf or "").strip()
    BOT_FEED_STATE["logged_in"] = True
    BOT_FEED_STATE["status"] = "starting"
    try:
        save_bot_config()
    except Exception:
        pass


def feed_logout():
    global q_instance, QUOTEX_SSID_TOKEN, QUOTEX_CSRF_TOKEN
    BOT_FEED_STATE["logged_in"] = False
    BOT_FEED_STATE["status"] = "offline"
    QUOTEX_SSID_TOKEN = ""
    QUOTEX_CSRF_TOKEN = ""
    try:
        save_bot_config()
    except Exception:
        pass
    client = q_instance
    q_instance = None
    if client is not None and AUTO_TRADE_LOOP is not None:
        async def _close(c):
            try:
                await c.close()
            except Exception:
                pass
        try:
            asyncio.run_coroutine_threadsafe(_close(client), AUTO_TRADE_LOOP)
        except Exception:
            pass


class BotControl:
    def __init__(self):
        self.token = BOT_TOKEN
        self.base = ("https://api.telegram.org/bot" + BOT_TOKEN + "/") if BOT_TOKEN else ""
        self.http = _requests.Session()
        self.stop_event = threading.Event()
        self.events = deque(maxlen=100)
        self.events_lock = threading.Lock()
        self.pending = {}
        self.generation = 0
        self.session_lock = threading.Lock()
        self.tunnel = QuickTunnel(PORT)

    def clean(self, text):
        text = str(text)
        for secret in (BOT_TOKEN, QUOTEX_SSID_TOKEN, QUOTEX_CSRF_TOKEN):
            if secret:
                text = text.replace(secret, "[HIDDEN]")
        return text[:3800]

    def event(self, text):
        line = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()) + " | " + self.clean(text)
        with self.events_lock:
            self.events.append(line)
        print(line, flush=True)

    def call(self, method, payload=None, timeout=20):
        if not self.base:
            return None
        try:
            response = self.http.post(self.base + method, json=payload or {}, timeout=timeout)
            data = response.json()
            if not data.get("ok"):
                self.event("Telegram API " + method + " failed (HTTP " + str(response.status_code) + ").")
                return None
            return data.get("result")
        except (_requests.RequestException, ValueError):
            self.event("Telegram API " + method + " temporarily unavailable.")
            return None

    def send(self, chat, text):
        return self.call("sendMessage", {"chat_id": chat, "text": self.clean(text)[:4000],
                                         "disable_web_page_preview": True})

    def erase(self, chat, message_id):
        self.call("deleteMessage", {"chat_id": chat, "message_id": message_id})

    def _watch(self, chat, version):
        last = None
        deadline = time.monotonic() + 120
        while version == self.generation and not self.stop_event.is_set():
            state = BOT_FEED_STATE.get("status")
            if state != last:
                last = state
                self.event("Quotex login state: " + str(state))
                if state == "online":
                    self.send(chat, """✅ Quotex login সফল। Live candle collection চলছে।

/server — public URL
/status — feed ও data status
/logout — broker logout (history/tunnel থাকবে)""")
                    return
                if state == "error":
                    self.send(chat, """❌ Login ব্যর্থ। Fresh Token/CSRF লাগবে, অথবা User-Agent মিলছে না।

আবার /start দিয়ে নতুন token দিন। /logs দেখুন।""")
                    return
            if time.monotonic() > deadline:
                if state != "online":
                    self.send(chat, """⏳ ২ মিনিটেও login নিশ্চিত হয়নি। /status দেখুন, অথবা /start দিয়ে fresh Token/CSRF দিন।""")
                return
            time.sleep(1)

    def _login(self, chat, ssid, csrf):
        with self.session_lock:
            self.generation += 1
            version = self.generation
        feed_login(ssid, csrf)
        self.event("Token/CSRF received; connecting to Quotex. Credentials hidden.")
        self.send(chat, "🔐 Token/CSRF পেয়েছি। Quotex connection যাচাই করছি…")
        threading.Thread(target=self._watch, args=(chat, version), daemon=True).start()

    def status_text(self):
        candles = sum(len(v) for v in MARKET_DATA.values())
        markets = len(MARKET_DATA)
        url = self.tunnel.url if self.tunnel.process and self.tunnel.process.poll() is None else "বন্ধ"
        return ("Feed: " + str(BOT_FEED_STATE.get("status")) +
                "\nCandles: " + str(candles) +
                "\nMarket keys: " + str(markets) +
                "\nToken session: " + ("set" if QUOTEX_SSID_TOKEN else "not set") +
                "\nTunnel: " + str(url) +
                "\nData dir: " + str(DATA_DIR))

    def _server(self, chat):
        try:
            url = self.tunnel.start()
            self.event("Public tunnel URL issued.")
            self.send(chat, "🌍 Public server URL:\n" + url +
                      "\n\nনতুন tunnel হলে URL বদলাবে। /logout দিলেও tunnel চালু থাকবে।")
        except Exception as exc:
            self.event("Tunnel failed: " + type(exc).__name__)
            self.send(chat, "❌ " + self.clean(str(exc)))

    def handle(self, message):
        chat = message.get("chat") or {}
        user = message.get("from") or {}
        if chat.get("type") != "private" or user.get("is_bot"):
            return
        chat_id, uid = chat.get("id"), user.get("id")
        if not isinstance(uid, int):
            return
        text = (message.get("text") or "").strip()
        command = text.split(maxsplit=1)[0].split("@")[0].lower() if text else ""

        if command in ("/start", "/login"):
            self.pending[uid] = {"step": "ssid", "expires": time.monotonic() + 300}
            online = BOT_FEED_STATE.get("status") == "online"
            note = "বর্তমান feed চালু আছে; নতুন token দিলে session বদলাবে।" if online else "আগের candle/history অক্ষত থাকবে।"
            self.send(chat_id, """🔐 Quotex SSID / Session Token পাঠান।
এরপর আলাদা message-এ CSRF (XSRF-TOKEN) চাইব।
অথবা এক message-এ JSON: {"token":"...","csrf":"..."}

৫ মিনিটের মধ্যে দিন। """ + note)
            return
        if command == "/cancel":
            self.pending.pop(uid, None)
            self.send(chat_id, "Login input বাতিল। /start দিয়ে আবার শুরু করুন।")
            return
        if command == "/logout":
            try:
                feed_logout()
                self.send(chat_id, """✅ Broker logout হয়েছে; Token/CSRF মুছে দেওয়া হয়েছে।
আগের candle/history ও tunnel URL চালু রাখা হয়েছে।
আবার login করতে /start দিন।""")
            except Exception as exc:
                self.event("Logout cleanup incomplete: " + type(exc).__name__)
                self.send(chat_id, "⚠️ Logout cleanup সময় শেষ; /status দেখুন।")
            return
        if command == "/server":
            if BOT_FEED_STATE.get("status") != "online":
                self.send(chat_id, "আগে /start দিয়ে Token/CSRF login সফল করুন।")
                return
            self.send(chat_id, "⏳ Cloudflare tunnel URL তৈরি করছি…")
            threading.Thread(target=self._server, args=(chat_id,), daemon=True).start()
            return
        if command == "/status":
            self.send(chat_id, self.status_text())
            return
        if command == "/logs":
            with self.events_lock:
                body = "\n".join(list(self.events)[-15:])
            self.send(chat_id, body or "এখনও log নেই।")
            return
        if command == "/help":
            self.send(chat_id, """/start — Token/CSRF দিয়ে Quotex login
/server — public Cloudflare URL
/status — feed ও data status
/logs — sanitized login log
/logout — broker logout (history থাকবে)
/cancel — login input বাতিল""")
            return
        if uid in self.pending:
            pending = self.pending[uid]
            self.erase(chat_id, message.get("message_id"))
            if time.monotonic() > pending["expires"]:
                self.pending.pop(uid, None)
                self.send(chat_id, "Login input expired। /start দিন।")
                return
            if not text or len(text) > 8192:
                self.send(chat_id, "Token/CSRF text invalid বা অনেক বড়। আবার দিন।")
                return
            if pending["step"] == "ssid":
                if text.startswith("{"):
                    try:
                        data = json.loads(text)
                        ssid = data.get("ssid_token") or data.get("token") or data.get("ssid")
                        csrf = data.get("csrf_token") or data.get("csrf") or ""
                        if not isinstance(ssid, str) or not ssid.strip():
                            raise ValueError()
                    except (ValueError, TypeError, AttributeError):
                        self.send(chat_id, "JSON-এ non-empty token দিন (csrf optional)।")
                        return
                    self.pending.pop(uid, None)
                    self._login(chat_id, ssid, csrf if isinstance(csrf, str) else "")
                else:
                    pending.update(step="csrf", ssid=text.strip().strip('"').strip("'"),
                                   expires=time.monotonic() + 300)
                    self.send(chat_id, "✅ SSID পেয়েছি। এবার CSRF / XSRF-TOKEN পাঠান (না থাকলে none লিখুন)।")
            else:
                self.pending.pop(uid, None)
                csrf = "" if text.lower() in ("none", "-", "skip", "no") else text.strip().strip('"').strip("'")
                self._login(chat_id, pending["ssid"], csrf)
            return
        if command.startswith("/"):
            self.send(chat_id, "Command পাওয়া যায়নি। /help দিন।")

    def poll(self):
        self.call("deleteWebhook", {"drop_pending_updates": True})
        self.call("setMyCommands", {"commands": [
            {"command": "start", "description": "Token/CSRF login"},
            {"command": "server", "description": "Public URL"},
            {"command": "status", "description": "Feed status"},
            {"command": "logs", "description": "Login logs"},
            {"command": "logout", "description": "Broker logout"},
            {"command": "cancel", "description": "Cancel input"}]})
        old = self.call("getUpdates", {"offset": -1, "timeout": 0})
        offset = old[-1]["update_id"] + 1 if old else 0
        while not self.stop_event.is_set():
            updates = self.call("getUpdates", {"offset": offset, "timeout": 20,
                                               "allowed_updates": ["message"]}, timeout=30)
            if updates is None:
                self.stop_event.wait(4)
                continue
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    self.handle(update.get("message") or {})
                except Exception as exc:
                    self.event("Telegram command failed: " + type(exc).__name__)
            for key, item in list(self.pending.items()):
                if time.monotonic() > item["expires"]:
                    self.pending.pop(key, None)

    def start(self):
        if not self.token:
            print("⚠️ BOT_TOKEN variable nei — Telegram control bot bondho, sudhu WEB UI cholbe.", flush=True)
            return False
        me = self.call("getMe", {})
        if not me:
            print("⚠️ BOT_TOKEN invalid — Telegram bot shuru hoyni.", flush=True)
            return False
        self.event("Telegram bot @" + str(me.get("username")) + " online. /start diye Token/CSRF din.")
        threading.Thread(target=self.poll, name="telegram-poll", daemon=True).start()
        return True


@app.get("/healthz")
def _healthz():
    return jsonify({"ok": True, "feed": BOT_FEED_STATE.get("status", "offline"),
                    "token_session": bool(QUOTEX_SSID_TOKEN)})



# ==========================================
# BOOT
# ==========================================
if __name__ == "__main__":
    load_signals()  # restore stored signal arrows (locks persist across restarts)

    # 1. Quotex data-feed worker (connects only after a token+CSRF login)
    threading.Thread(target=start_async_loop, daemon=True).start()

    # 2. Telegram control bot — needs ONLY BOT_TOKEN
    BOT_CONTROL = BotControl()
    BOT_CONTROL.start()
    atexit.register(lambda: BOT_CONTROL.stop_event.set())

    # 3. Flask web server (serves the embedded UI)
    print(f"🚀 HyperTrade server on http://{HOST}:{PORT}  |  Telegram: /start")
    app.run(host=HOST, port=PORT, threaded=True, debug=False, use_reloader=False)
