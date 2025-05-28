# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, jsonify, request, url_for
import requests, os, json, time, platform
from bs4 import BeautifulSoup
from collections import defaultdict
from functools import lru_cache
from datetime import datetime, timedelta

# 全局配置
QUERY_INTERVAL = 0
Bui = '1.1.1'
query_timestamps = defaultdict(list)
header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"}

Base_html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CR Train Tracker</title>
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">

    <!-- 页面主样式 -->
    <style>
        body {
            background: #f5f5f7;
            color: #1d1d1f;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }

        /* 主标题样式 */
        h1 {
            font-size: 2.8rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            text-align: center;
            padding: 60px 20px 40px;
            color: #000;
        }

        /* 搜索栏区域 */
        .search-container {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            margin: 20px auto 40px;
            max-width: 640px;
            padding: 0 20px;
        }
        .search-box {
            flex: 1;
            height: 50px;
            border: 1px solid #d2d2d7;
            border-radius: 14px;
            padding: 0 18px;
            font-size: 1.05rem;
            background: #fff;
            transition: border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }
        .search-box:focus {
            border-color: #0071e3;
            box-shadow: 0 0 0 3px rgba(0,113,227,0.2);
            outline: none;
        }
        .search-btn, .toggle-history-btn {
            height: 50px;
            padding: 0 22px;
            border-radius: 14px;
            font-size: 1rem;
            font-weight: 500;
            border: 1px solid #0071e3;
            background-color: #fff;
            color: #0071e3;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        .search-btn:hover, .toggle-history-btn:hover {
            background-color: #0071e3;
            color: #fff;
        }
        .search-btn:disabled {
            color: #aaa;
            border-color: #ccc;
            cursor: not-allowed;
            background: #f5f5f7;
        }

        /* 查询类型选项区 */
        .option-container {
            background: #fff;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
            border-radius: 16px;
            padding: 20px;
            margin: 0 auto 40px;
            max-width: 700px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        .radio-group {
            display: flex;
            gap: 14px;
        }
        .radio-option {
            font-size: 0.95rem;
            color: #1d1d1f;
            display: flex;
            align-items: center;
        }
        .radio-option input {
            margin-right: 6px;
        }
        .hint-text {
            width: 100%;
            font-size: 0.9rem;
            color: #6e6e73;
            margin-top: 12px;
            text-align: center;
        }

        /* 收藏夹区域 */
        .history-panel {
            background: #fff;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
            border-radius: 16px;
            padding: 20px;
            margin: 0 auto 40px;
            max-width: 700px;
            display: none;
        }

        /* 查询结果区域 */
        .result-container {
            max-width: 800px;
            margin: 0 auto 20px;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            padding: 24px;
        }
        #resultContainer:empty {
            display: none;
        }
        .result-item {
            padding: 20px 0;
            border-bottom: 1px solid #e5e5ea;
        }
        .result-item:last-child {
            border-bottom: none;
        }
        .result-item h3 {
            font-size: 1.15rem;
            font-weight: 600;
            margin-bottom: 8px;
            color: #0071e3;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .result-item p {
            margin: 4px 0;
            font-size: 0.96rem;
            color: #1d1d1f;
        }

        /* 友情链接与版本信息 */
        .credits-container {
            max-width: 700px;
            margin: 20px auto 10px;
            padding: 10px 0;
            border-top: 1px solid #ccc;
            text-align: center;
            font-size: 0.9rem;
            color: #6e6e73;
        }
        .credit-link {
            color: #0071e3;
            text-decoration: none;
            margin: 0 6px;
        }
        .credit-link:hover {
            text-decoration: underline;
        }
        .credits-title {
            text-align: center;
            margin-top: 10px;
            font-size: 0.85rem;
            color: #8e8e93;
        }

        /* 响应式布局 */
        @media (max-width: 768px) {
            .search-container {
                flex-direction: column;
                gap: 12px;
            }
            .search-btn, .toggle-history-btn, .search-box {
                width: 100%;
            }
            .option-container {
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
            }
            .hint-text {
                text-align: left;
            }
        }
    </style>

    <!-- 载入动画及收藏面板样式 -->
    <style>
        .loading-spinner {
            border: 4px solid rgba(0, 113, 227, 0.2);
            border-top: 4px solid #0071e3;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 0.8s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="main-content" data-cooldown="{{ cooldown_remaining }}" data-query-interval="{{ QUERY_INTERVAL }}">
        <!-- 页面主标题 -->
        <h1>CR Train Tracker</h1>

        <!-- 搜索栏区域 -->
        <div class="search-container">
            <input type="text" class="search-box" id="searchInput" placeholder="输入内容" maxlength="15">
            <button id="toggleHistory" class="toggle-history-btn">显示收藏</button>
            <button class="search-btn" id="searchBtn" disabled>查询</button>
        </div>

        <!-- 查询类型选项区 -->
        <div class="option-container">
            <div class="radio-group">
                <label class="radio-option"><input type="radio" name="searchType" value="trainId" checked>车号</label>
                <label class="radio-option"><input type="radio" name="searchType" value="trainCode">车次</label>
            </div>
            <div id="routeOptionContainer">
                <label class="route-option">
                    <input title="关闭后查询速度能提升约750%" type="checkbox" id="showRoutes"> 显示交路
                </label>
            </div>
            <div class="hint-text" id="hintText">输入车号，如CR400BF-5033</div>
        </div>

        <!-- 收藏夹区域 -->
        <div class="history-panel" id="historyPanel">
            <div style="font-weight:bold; display:flex; justify-content:space-between; align-items:center;">
                <span>我的收藏</span>
                <span id="favoriteCount" style="font-size:0.8em; color:#b0b0b0;">共 0 个</span>
            </div>
            <div id="MyFavorite"><p style="color:#b0b0b0; padding:10px; text-align:center;">暂无收藏</p></div>
        </div>

        <!-- 查询结果区域 -->
        <div class="result-container" id="resultContainer"></div>
    </div>

    <!-- 友情链接与内容来源 -->
    <div class="credits-container">
        <div>友情链接 & 内容来源 ; 版本 : '''+ Bui +'''</div>
        <div class="resource">
            <a href="http://rail.re/" target="_blank" class="credit-link">铁路信息查询:交路查询返回</a>
            <a href="https://emu.passearch.info/" target="_blank" class="credit-link">EmuSearch列车配属查询:信息查询返回</a>
            <a href="https://www.china-emu.cn/" target="_blank" class="credit-link">China-Emu列车大全:网页内列车图标</a>
        </div>
    </div>

    <script>
    // ========== 全局变量 ==========
    const QUERY_INTERVAL = parseInt(document.querySelector('.main-content').dataset.queryInterval) || '''+ str(QUERY_INTERVAL) +''';
    let lastQueryTime = 0;
    let cooldownInterval;
    let favorites = JSON.parse(localStorage.getItem('train_favorites')) || [];
    window.searchFavorite = searchFavorite;
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const resultContainer = document.getElementById('resultContainer');
    const historyPanel = document.getElementById('historyPanel');
    const MyFavorite = document.getElementById('MyFavorite');
    const toggleHistoryBtn = document.getElementById('toggleHistory');
    const favoriteCount = document.getElementById('favoriteCount');

    // 页面初始化事件
    document.addEventListener('DOMContentLoaded', () => {
        loadFavorites();
        updateFavoriteCount();

        const mainContent = document.querySelector('.main-content');
        const initialCooldown = parseInt(mainContent.dataset.cooldown) || 0;
        if (initialCooldown > 0) {
            lastQueryTime = Date.now() / 1000 - (QUERY_INTERVAL - initialCooldown);
            startCooldown();
        }
        searchInput.addEventListener('input', updateSearchBtnState);
        const routeOptionContainer = document.getElementById('routeOptionContainer');
        document.querySelectorAll('input[name="searchType"]').forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.value === 'trainId') {
                    routeOptionContainer.style.display = 'block';
                } else {
                    routeOptionContainer.style.display = 'none';
                }
            });
        });
    });

    // 检查冷却初始化
    function checkInitialCooldown() {
        const now = Date.now() / 1000;
        if (now - lastQueryTime < QUERY_INTERVAL) {
            startCooldown();
        }
    }

    // 启动冷却倒计时
    function startCooldown() {
        let remainingSeconds = QUERY_INTERVAL;
        searchBtn.classList.add('cooldown');
        searchBtn.disabled = true;
        searchBtn.textContent = `冷却中 (${remainingSeconds}s)`;
        if (cooldownInterval) clearInterval(cooldownInterval);
        cooldownInterval = setInterval(() => {
            remainingSeconds--;
            if (remainingSeconds <= 0) {
                clearInterval(cooldownInterval);
                endCooldown();
            } else {
                searchBtn.textContent = `冷却中 (${remainingSeconds}s)`;
            }
        }, 1000);
    }
    function endCooldown() {
        searchBtn.classList.remove('cooldown');
        searchBtn.textContent = '查询';
        updateSearchBtnState();
    }

    // 收藏夹相关操作
    function saveFavorites() {
        localStorage.setItem('train_favorites', JSON.stringify(favorites));
        updateFavoriteCount();
    }
    function updateFavoriteCount() {
        favoriteCount.textContent = `共 ${favorites.length} 个`;
    }
    function toggleFavorite(trainId, modelName, display = '', group = '') {
        const isFavorite = favorites.some(fav => fav.id === trainId);
        if (group === '贵阳市域铁路') { group = '郑州铁路局'; }
        else if (group === '广东城际') { group = '广州铁路集团'; }
        else if (group === '铁科院') { group = 'CARS'; }
        if (isFavorite) {
            favorites = favorites.filter(fav => fav.id !== trainId);
        } else {
            favorites.push({
                id: trainId, name: modelName, display: display, group: group, timestamp: new Date().toISOString()
            });
        }
        saveFavorites();
        updateFavoriteButtons();
        renderFavorites();
    }
    function searchFavorite(trainName) {
        searchInput.value = trainName;
        updateSearchBtnState();
        document.querySelector('input[name="searchType"][value="trainId"]').checked = true;
        document.getElementById('hintText').textContent = '输入车号，如CR400BF-5033';
        searchInput.placeholder = '输入车号';
        if (searchBtn.disabled === false) {
            handleSearch();
        }
    }
    function renderFavorites() {
        const sortedFavorites = [...favorites].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        MyFavorite.innerHTML = sortedFavorites.map(fav => `
            <div class="favorite-item" onclick="searchFavorite('${fav.name}')">
                <img src="https://www.china-emu.cn/img/Cute/${fav.display}.png" style="width:32px;height:32px;vertical-align:middle;margin-right:8px;">
                <button class="favorite-btn active" onclick="event.stopPropagation(); toggleFavorite('${fav.id}', '${fav.name}')" title="点击取消收藏 ${fav.name}">★</button>
                <span>${fav.name}</span>
                <img src="/static/${fav.group}.png" style="width:32px;height:32px;vertical-align:middle;margin-right:8px;">
            </div>
        `).join('') || '<p style="color:#b0b0b0; width:100%; text-align:center;">暂无收藏</p>';
    }
    function loadFavorites() { renderFavorites(); }
    function updateFavoriteButtons() {
        document.querySelectorAll('.favorite-btn').forEach(btn => {
            const trainId = btn.dataset.train;
            if (trainId) {
                const isFavorite = favorites.some(fav => fav.id === trainId);
                btn.classList.toggle('active', isFavorite);
                btn.title = isFavorite ? '取消收藏' : '收藏此车组';
            }
        });
    }
    toggleHistoryBtn.addEventListener('click', () => {
        const isShowing = historyPanel.style.display === 'block';
        historyPanel.style.display = isShowing ? 'none' : 'block';
        toggleHistoryBtn.textContent = isShowing ? '显示收藏' : '隐藏收藏';
    });

    // 搜索按钮状态联动
    function updateSearchBtnState() {
        if (searchInput.value.trim()) {
            searchBtn.classList.add('active');
            searchBtn.disabled = false;
        } else {
            searchBtn.classList.remove('active');
            searchBtn.disabled = true;
        }
    }

    // 搜索按钮点击事件
    searchBtn.addEventListener('click', handleSearch);

    // 发起搜索请求并展示结果
    async function handleSearch() {
        const now = Date.now() / 1000;
        const QUERY_INTERVAL = parseInt(document.querySelector('.main-content').dataset.queryInterval);
        if (now - lastQueryTime < QUERY_INTERVAL) {
            handleQueryCooldown(now);
            return;
        }
        const keyword = searchInput.value.trim();
        if (!keyword) return;
        const searchType = document.querySelector('input[name="searchType"]:checked').value;
        setSearchState('查询中...', true);
        resultContainer.innerHTML = '<div class="loading-spinner"></div><p style="text-align:center;">正在查询中，请稍候...</p>';
        resultContainer.style.display = 'block';
        const showRoutes = document.getElementById('showRoutes').checked;
        try {
            const response = await fetch(`/search_train?type=${searchType}&keyword=${encodeURIComponent(keyword)}&show_routes=${showRoutes}`);
            const data = await response.json();
            if (!data.success) {
                resultContainer.innerHTML = `<p>${data.message || '查询失败'}</p>`;
                return;
            }
            renderResults(data);
            lastQueryTime = Date.now() / 1000;
            startCooldown(QUERY_INTERVAL);
        } catch (e) {
            resultContainer.innerHTML = `<p>查询出错: ${e.message}</p>`;
        } finally {
            setSearchState('查询', false);
        }
    }
    // 冷却期间处理
    function handleQueryCooldown(now) {
        const QUERY_INTERVAL = parseInt(document.querySelector('.main-content').dataset.queryInterval) || 6;
        const waitTime = Math.ceil(QUERY_INTERVAL - (now - lastQueryTime));
        startCooldown(waitTime);
        const timer = setInterval(() => {
            const remaining = Math.ceil(QUERY_INTERVAL - (Date.now() / 1000 - lastQueryTime));
            if (remaining <= 0) {
                clearInterval(timer);
                searchBtn.classList.remove('cooldown');
                updateSearchBtnState();
                searchBtn.textContent = `查询`;
            } else {
                searchBtn.textContent = `冷却中 (${remaining}s)`;
            }
        }, 1000);
    }
    function setSearchState(text, disabled) {
        searchBtn.textContent = text;
        searchBtn.disabled = disabled;
    }
    // 渲染查询结果
    function renderResults(data) {
        resultContainer.innerHTML = '';
        if (data.results && data.results.length > 0) {
            const countDiv = document.createElement('div');
            countDiv.className = 'result-count';
            countDiv.innerHTML = `共找到${data.count || data.results.length}条结果 ${data.Sj || ''} <span class="query-time">查询用时${data.query_time || ''}</span><br>`;
            resultContainer.appendChild(countDiv);
            data.results.forEach(result => {
                const trainId = `${result.车型}${result.车组号}`;
                const modelName = `${result.车型}-${result.车组号}`;
                const group = `${result.logo}`;
                const display = `${result.display}`;
                const isFavorite = favorites.some(fav => fav.id === trainId);
                const itemDiv = document.createElement('div');
                itemDiv.className = 'result-item';
                itemDiv.innerHTML = `
                    <h3>
                        <button class="favorite-btn ${isFavorite ? 'active' : ''}" data-train="${trainId}" onclick="toggleFavorite('${trainId}', '${modelName}', '${display}', '${group}')" title="${isFavorite ? '取消收藏' : '收藏此车组'}">★</button>
                        ${result.车型顶显示}-${result.车组号}
                        ${result.other_icon}
                        <a href="https://rail.re/#${result.车型}${result.车组号}" target="_blank" style="color: #C2D2FF;" title="点击查看${result.车型}-${result.车组号}的交路信息">${result.交路}</a>
                    </h3>
                    <p><strong>配属路局:</strong>${result.配属路局}</p>
                    <p><strong>配属动车所:</strong>${result.配属动车所}</p>
                    <p><strong>生产厂家:</strong>${result.生产厂家}</p>
                    ${result.备注 ? `<p><strong>备注:</strong>${result.备注}</p>` : ''}
                    <p>内容来源:
                        <a href="https://emu.passearch.info/?type=number&keyword=${result.车组号}" target="_blank" title="点击查看${result.车型}-${result.车组号}的交路信息" style="color: #C2D2FF;">EmuSearch</a>
                        <a href="https://rail.re/#${result.车型}${result.车组号}" target="_blank" title="点击查看详情" style="color: #C2D2FF;">${result.is_search_jl}</a>
                    </p>
                `;
                resultContainer.appendChild(itemDiv);
            });
        } else {
            resultContainer.innerHTML = '<p>未找到匹配结果</p>';
        }
    }

    // 搜索类型切换提示文字
    document.querySelectorAll('input[name="searchType"]').forEach(radio => {
        radio.addEventListener('change', function () {
            document.getElementById('hintText').textContent =
                this.value === 'trainCode' ? '输入车次，如G690' : '输入车号，如CR400BF-5033';
            searchInput.placeholder = this.value === 'trainCode' ? '输入车次' : '输入车号';
        });
    });
    searchInput.addEventListener('input', updateSearchBtnState);
    window.toggleFavorite = toggleFavorite;
    </script>
</body>
</html>
'''


app = Flask(__name__)

def dicf(keys, value):
    return dict.fromkeys(keys, value)

CRH6A_B_RANGES = [(656, 666), (675, 682)]
CRH6A_C_NUMBERS = ['0644', '0645', '0646', '0647', '0648', '0652', '0653', '0654', '0655']
MODEL_DISPLAY_MAP = {
    'CR450AF': 'CR450AFs',
    'CR450BF': 'CR450BFs',
    **dicf(['CR400AF-A', 'CR400AF-B'], 'CR400AF'),
    **dicf(['CR400AF-AE', 'CR400AF-S', 'CR400AF-AS', 'CR400AF-AZ', 'CR400AF-BS', 'CR400AF-BZ', 'CR400AF-Z'], 'CR400AF-C'),
    **dicf(['CR400BF-A', 'CR400BF-B', 'CR400BF-C'], 'CR400BF'),
    **dicf(['CR400BF-AS', 'CR400BF-BS', 'CR400BF-GS'], 'CR400BF-S'),
    **dicf(['CR400BF-AZ', 'CR400BF-BZ', 'CR400BF-GZ'], 'CR400BF-Z'),
    **dicf(['CR300AF-A', 'CR300AF-B'], 'CR300AF'),
    **dicf(['CRH380AL', 'CRH380AN'], 'CRH380A'),
    'CRH380BL': 'CRH380B',
    'CRH380CL': 'CRH380C',
    'CRH2B': 'CRH2A',
    'CRH1B': 'CRH1A',
    'CRH6A-A': 'CRH6A',
    'CRH6F': 'CRH6F',
    'CRH6F-A': 'CRH6F-A',
    'CRH3A-A': 'CRH3A-A'
}

SPECIAL_RULES = {
    'CR400BF-J': {
        '0001': 'CR400BF-J',
        '0003': 'CR400BF-J-0003',
    },
    'CR400AF-J': {
        '0002': 'CR400AF-J',
    },
    'CR400BF-C': {
        '5162': 'CR400BF-C-5162',
    },
    'CR400BF-Z': {
        '0524': 'CR400BF-Z-0524',
    },
    'CRH380A': {
        'range': [(251, 259)],
        'display_model': 'CRH380M',
    },
    'CRH6A-A': {
        'range': [(212, 216)],
        **{f"{i:04d}": 'CRH6A-B' for start, end in CRH6A_B_RANGES for i in range(start, end + 1)},
        **dicf(CRH6A_C_NUMBERS, 'CRH6A-C'),
    },
    'CRH6F': {
        **dicf(['0651', '0650', '0479'], 'CRH6A-B'),
        '0001': 'CRH6A',
        **dicf(['0409', '0410', '0411', '0412', '0413'], 'CRH6F'),
        **dicf(['0418', '0419', '0474', '0475', '0476', '0477'], 'CRH6A-C'),
    },
    'CRH6F-A': {
        **dicf(['0440', '0441', '0442'], 'CRH6F-SX'),
        '0443': 'CRH6A-C',
        '0211': 'CRH6FA0500',
        '0499': 'CRH6FA0499',
        **dicf(['0445', '0446', '0447', '0448', '0449', '0450'], 'CRH6F'),
        **dicf(['0461', '0462', '0463', '0464', '0465', '0466', '0467', '0497', '0498'], 'CRH6F-AC'),
        **dicf(['0468', '0469', '0470'], 'CRH6F-A'),
        **dicf(['0471', '0472', '0473'], 'CRH6A-C'),
        **dicf(['0491', '0492', '0493', '0494', '0495', '0496'], 'CRH6F-BJS5'),
    },
    'CRH2A': {
        '2460': 'CRH2G',
    },
    'CRH2E': {
        'range': [(2461, 2466)],
    },
    'CRH2G': {
        'range': [(2417, 2426), (4072, 4082), (4106, 4114)],
    },
}


@app.route('/')
def index():
    return render_template_string(Base_html_template, Bui=Bui, cooldown_remaining=0)


@app.route('/search_train')
def search_train():
    show_routes = request.args.get('show_routes', 'false').lower() == 'true'
    start_time = time.time()
    client_ip = request.remote_addr
    current_time = time.time()

    if query_timestamps[client_ip] and current_time - query_timestamps[client_ip][-1] < QUERY_INTERVAL:
        wait_time = int(QUERY_INTERVAL - (current_time - query_timestamps[client_ip][-1]))
        return jsonify({
            'success': False,
            'message': f'查询间隔太短,请等待{wait_time}秒后再试'
        })

    query_timestamps[client_ip].append(current_time)
    search_type = request.args.get('type')
    keyword = request.args.get('keyword')
    digits = ''.join([c for c in keyword if c.isdigit()])
    clean_keyword = digits[-4:] if len(digits) >= 4 else "格式错误!"

    if search_type == 'trainId':
        try:
            api_url = f"https://emu.passearch.info/?type=number&keyword={clean_keyword}"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            try:
                soup = BeautifulSoup(response.text, 'html5lib')
            except Exception:
                try:
                    soup = BeautifulSoup(response.text, 'lxml')
                except Exception:
                    soup = BeautifulSoup(response.text, 'html.parser')

            results_table = None
            for table in soup.find_all('table'):
                headers = [th.get_text(strip=True) for th in table.find_all('th')]
                if '配属路局' in headers and '车组号' in headers:
                    results_table = table
                    break
            if not results_table:
                return jsonify({'success': False, 'message': '无结果'})

            rows = results_table.find_all('tr')[1:]
            results = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 7:
                    continue
                original_model = cols[0].get_text(strip=True)
                current_number = cols[1].get_text(strip=True)
                display_model = MODEL_DISPLAY_MAP.get(original_model, original_model.split('-')[0])
                if original_model in SPECIAL_RULES:
                    rules = SPECIAL_RULES[original_model]
                    if 'range' in rules:
                        num = int(current_number)
                        for start, end in rules['range']:
                            if start <= num <= end:
                                display_model = rules.get('display_model', rules.get(str(num), original_model))
                                break
                    if current_number in rules:
                        display_model = rules[current_number]

                other_icon = ''
                jl = ''
                is_search_jl = ''
                ltd = cols[4].get_text(strip=True)
                gr = logo = cols[2].get_text(strip=True)

                if show_routes:
                    if gr not in ['铁科院', '中国铁路总公司', '']:
                        url = f"https://api.rail.re/emu/{original_model}{current_number}"
                        jl_h5 = requests.get(url, headers=header, timeout=5)
                        jl_h5.encoding = "utf-8"
                        if jl_h5.text not in ['[]', '']:
                            route_data = json.loads(jl_h5.text)
                            if route_data:
                                first_date = route_data[0]['date'].split()[0]
                                jl = route_data[0]['date'] + ' ' + '担当车次: ' + route_data[0]['train_no']
                                for item in route_data[1:1]:
                                    current_date = item['date'].split()[0]
                                    if current_date == first_date:
                                        jl += ' ' + item['train_no']
                                    else:
                                        break
                # 归一化logo
                if gr == '贵阳市域铁路':
                    logo = '郑州铁路局'
                if gr == '金台铁路':
                    logo = '上海铁路局'
                if gr == '成都市域铁路':
                    logo = '成都铁路局'
                if ltd == '广东浦镇':
                    ltd = '江门中车或南京浦镇'
                if gr == '广东城际':
                    other_icon = f'<img title={gr} src="{url_for("static", filename="广州铁路集团.png")}" width=32 height="32">'
                if gr == '铁科院':
                    logo = 'CARS'
                if gr:
                    other_icon += f'<img title="{gr}" src="{url_for("static", filename=logo + ".png")}" width=32 height="32">'
                model_with_icon = (
                    f'<img title="{ltd}{original_model}-{current_number}" '
                    f'src="https://www.china-emu.cn/img/Cute/{display_model}.png" '
                    f'style="width:32px;height:32px;vertical-align:middle;margin-right:8px;">{original_model}'
                )
                if cols[5].get_text(strip=True) == '公务车':
                    other_icon += (
                        '<img src="/static/公务车.png" '
                        'style="width:32px;height:32px;vertical-align:middle;margin-right:8px;">'
                    )
                local_time = time.localtime(current_time)
                Sj = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
                if original_model + current_number == keyword or original_model[:5] == keyword[:5]:
                    results.clear()
                    results.append({
                        'other_icon': other_icon,
                        'display': display_model,
                        'logo': logo,
                        '交路': jl,
                        '车型顶显示': model_with_icon,
                        '车型': original_model,
                        '车组号': current_number,
                        '配属路局': gr,
                        '配属动车所': cols[3].get_text(strip=True),
                        '生产厂家': ltd,
                        '备注': cols[5].get_text(strip=True)
                    })
                    break
                if show_routes:
                    is_search_jl = '铁路信息查询'
                results.append({
                    'is_search_jl': is_search_jl,
                    'other_icon': other_icon,
                    'display': display_model,
                    'logo': logo,
                    '交路': jl,
                    '车型顶显示': model_with_icon,
                    '车型': original_model,
                    '车组号': current_number,
                    '配属路局': gr,
                    '配属动车所': cols[3].get_text(strip=True),
                    '生产厂家': ltd,
                    '备注': cols[5].get_text(strip=True)
                })

            return jsonify({
                'success': True,
                'results': results,
                'count': len(results),
                'Sj': Sj,
                'query_time': f'{time.time() - start_time:.1f}s'
            })

        except requests.exceptions.RequestException as e:
            return jsonify({'success': False, 'message': f'网络请求失败:{str(e)}'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'查询失败:{str(e)}'})

    if search_type == 'trainCode':
        url = f"https://api.rail.re/train/{keyword}"
        jl_h5 = requests.get(url, headers=header, timeout=5)
        jl_h5.encoding = "utf-8"
        if jl_h5.text not in ['[]', '']:
            train_data = json.loads(jl_h5.text)
            if train_data:
                latest_record = train_data[0]
                date = latest_record['date']
                emu_no = latest_record['emu_no']
                train_no = latest_record['train_no']
                result = f"{date} 担当车次: {train_no}"
                first_date = datetime.strptime(date.split()[0], '%Y-%m-%d')
                for item in train_data[1:3]:
                    current_date = datetime.strptime(item['date'].split()[0], '%Y-%m-%d')
        else:
            return jsonify({'success': False, 'message': '未查询到该车次信息'})

        keyword = emu_no
        digits = ''.join([c for c in keyword if c.isdigit()])
        clean_keyword = digits[-4:] if len(digits) >= 4 else "格式错误!"
        api_url = f"https://emu.passearch.info/?type=number&keyword={clean_keyword}"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        try:
            soup = BeautifulSoup(response.text, 'html5lib')
        except Exception:
            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except Exception:
                soup = BeautifulSoup(response.text, 'html.parser')

        results_table = None
        for table in soup.find_all('table'):
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            if '配属路局' in headers and '车组号' in headers:
                results_table = table
                break
        if not results_table:
            return jsonify({'success': False, 'message': '无结果'})

        rows = results_table.find_all('tr')[1:]
        results = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 7:
                continue
            original_model = cols[0].get_text(strip=True)
            current_number = cols[1].get_text(strip=True)
            display_model = MODEL_DISPLAY_MAP.get(original_model, original_model.split('-')[0])
            if original_model in SPECIAL_RULES:
                rules = SPECIAL_RULES[original_model]
                if 'range' in rules:
                    num = int(current_number)
                    for start, end in rules['range']:
                        if start <= num <= end:
                            display_model = rules.get('display_model', rules.get(str(num), original_model))
                            break
                if current_number in rules:
                    display_model = rules[current_number]
            other_icon = ''
            jl = ''
            ltd = cols[4].get_text(strip=True)
            gr = logo = cols[2].get_text(strip=True)
            if gr == '贵阳市域铁路':
                logo = '郑州铁路局'
            if ltd == '广东浦镇':
                ltd = '江门中车或南京浦镇'
            if gr == '广东城际':
                other_icon = f'<img title={gr} src="{url_for("static", filename="广州铁路集团.png")}" width=32 height="32">'
            if gr == '铁科院':
                logo = 'CARS'
            if gr:
                other_icon += f'<img title="{gr}" src="{url_for("static", filename=logo + ".png")}" width=32 height="32">'
            model_with_icon = (
                f'<img title="{ltd}{original_model}-{current_number}" '
                f'src="https://www.china-emu.cn/img/Cute/{display_model}.png" '
                f'style="width:32px;height:32px;vertical-align:middle;margin-right:8px;">{original_model}'
            )
            local_time = time.localtime(current_time)
            Sj = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
            if original_model + current_number == emu_no or original_model[:6] == emu_no[:6]:
                results.clear()
                results.append({
                    'other_icon': other_icon,
                    'display': display_model,
                    'logo': logo,
                    '交路': result,
                    '车型顶显示': model_with_icon,
                    '车型': original_model,
                    '车组号': current_number,
                    '配属路局': gr,
                    '配属动车所': cols[3].get_text(strip=True),
                    '生产厂家': ltd,
                    '备注': cols[5].get_text(strip=True)
                })
                break
            if cols[5].get_text(strip=True) == '公务车':
                other_icon += (
                    '<img src="/static/公务车.png" '
                    'style="width:32px;height:32px;vertical-align:middle;margin-right:8px;">'
                )
            results.append({
                'is_search_jl': '铁路信息查询',
                'other_icon': other_icon,
                'display': display_model,
                'logo': logo,
                '交路': result,
                '车型顶显示': model_with_icon,
                '车型': original_model,
                '车组号': current_number,
                '配属路局': gr,
                '配属动车所': cols[3].get_text(strip=True),
                '生产厂家': ltd,
                '备注': cols[5].get_text(strip=True)
            })

        return jsonify({
            'success': True,
            'results': results,
            'Sj': Sj,
            'count': len(results),
            'query_time': f'{time.time() - start_time:.1f}s'
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5033)