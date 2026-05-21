# -*- coding: utf-8 -*-
import random
import re
from flask import Flask, render_template, request, session, redirect, url_for
from questions import QUESTIONS
from db import init_db, save_exam, get_exam_list, get_exam_detail, get_wrong_question_ids, get_all_students, get_score_leaderboard, get_total_leaderboard

app = Flask(__name__)
app.secret_key = 'csp-j-mock-exam-2024-secret-key'

init_db()

SOURCE_RULES = [
    (["二进制", "十进制", "十六进制", "八进制", "ASCII", "补码", "原码", "反码",
      "编码", "GB等于", "MB等于", "KB等于", "字节", "位二进制", "小数.*二进制",
      "二进制.*小数", "进制数", "进制之间", r"\d+位二进制", "十六进制整数"],
     "CSP-J 数制与编码"),
    (["栈", "入栈", "出栈", "队列", "入队", "出队", "链表", "链式存储", "二叉树",
      "完全二叉树", "图", "无向图", "顶点.*边", "线性表", "顺序表", "头结点",
      r"顺序.*存储", "循环队列", "前缀表达式", "后缀表达式", "中缀表达式",
      "遍历"],
     "CSP-J 数据结构"),
    (["排序", "查找", "搜索", "递归", "贪心", "动态规划", "分治", "时间复杂度",
      "空间复杂度", "KMP", "Huffman", "哈夫曼", "递推", "算法", "深度优先", "DFS",
      "广度优先", "BFS", "字符串匹配", "冒泡", "归并", "快速", "插入", "选择",
      "希尔", "二分查找", "顺序查找", "平均查找长度", "卡特兰"],
     "CSP-J 算法"),
    (["C\\+\\+", "cout", r"\bcin\b", r"\bint\b", r"\bchar\b", r"\bbool\b",
      "string", "sizeof", r"\bconst\b", "static", "引用", "指针", "函数重载",
      "模板", "重载", "构造函数", "析构", "数组下标", r"\bfor\b", r"\bwhile\b",
      "switch", "do-while", "变量", "函数.*声明", "STL", "vector", "list",
      "deque", "map", "运算符", "取地址", "continue", "break", "new", "delete",
      "头文件", "标识符", r"合法.*变量名", r"\bi\+\+\b", r"\+\+i", "函数模板",
      "bool类型", r"\.length\(\)", "stoi", "0x", "命名规则", "函数定义",
      r"int a\[\d+\]"],
     "CSP-J C++程序设计"),
    (["IP", "DNS", "HTTP", "HTTPS", "FTP", "SMTP", "TCP", "UDP", "协议",
      "端口", "网络", "局域网", "LAN", "WAN", "WLAN", "MAN", "OSI", "拓扑",
      "私有地址", "IPv4", "IPv6", "域名", "浏览器", "Web", "网络层",
      "覆盖范围"],
     "CSP-J 计算机网络"),
    (["操作系统", "编译程序", "编译.*解释", "计算机系统", "CPU", "运算器",
      "控制器", "内存", "硬盘", "RAM", "ROM", "Cache", "缓存", "寄存器",
      "系统软件", "应用软件", "输入设备", "输出设备", "显示器", "键盘",
      "鼠标", "扫描仪", "计算机病毒", "指令系统", "指令.*操作", r"\bCache\b",
      r"\bROM\b.*\bRAM\b", r"\bRAM\b.*\bROM\b", "只读存储器", "随机存取",
      r"\bCPU\b.*组成", "中央处理器", "计算机.*系统.*包括", "输出设备",
      r"操作系统.*功能", "最底层的软件", "编译型语言", "一条指令",
      "程序执行过程", "程序设计语言", "面向对象", "封装", "继承", "多态",
      "数据库", "关系型", "元组", "字段.*属性", "记录"],
     "CSP-J 计算机基础与系统"),
    (["逻辑", "真值", "布尔", "异或", "同或", "与.*或.*非", r"∧|∨|¬|⊕|↔",
      "排列", "组合", "三位偶数", "三位数", "任取", "卡片"],
     "CSP-J 数学与逻辑"),
]


def get_source(question):
    if question.get('source'):
        return question['source']
    text = question['question'] + ' ' + ' '.join(question['options'])
    for keywords, label in SOURCE_RULES:
        for kw in keywords:
            if re.search(kw, text):
                return label
    return "CSP-J 综合知识"


@app.route('/')
def index():
    exam_count = len(get_exam_list(limit=100))
    students = get_all_students()
    return render_template('index.html', question_count=len(QUESTIONS), exam_count=exam_count, students=students)


@app.route('/start', methods=['POST'])
def start():
    count = min(int(request.form.get('count', 10)), len(QUESTIONS))
    student_name = request.form.get('student_name', '').strip()
    selected = random.sample(QUESTIONS, count)
    session['questions'] = [q['id'] for q in selected]
    session['answers'] = {}
    session['student_name'] = student_name
    session['wrong_only'] = False
    return render_template('quiz.html', questions=selected, enumerate=enumerate, get_source=get_source, student_name=student_name)


@app.route('/start-wrong', methods=['POST'])
def start_wrong():
    student_name = request.form.get('student_name', '').strip()
    wrong_ids = get_wrong_question_ids(student_name=student_name if student_name else None)
    if not wrong_ids:
        return render_template('index.html',
                               question_count=len(QUESTIONS),
                               exam_count=len(get_exam_list(limit=100)),
                               students=get_all_students(),
                               error='还没有错题记录，请先完成至少一次考试！')

    count = min(int(request.form.get('count', 10)), len(wrong_ids))
    selected_ids = random.sample(wrong_ids, count)
    id_to_q = {q['id']: q for q in QUESTIONS}
    selected = [id_to_q[qid] for qid in selected_ids if qid in id_to_q]

    if not selected:
        return render_template('index.html',
                               question_count=len(QUESTIONS),
                               exam_count=len(get_exam_list(limit=100)),
                               students=get_all_students(),
                               error='错题数据异常，请先完成新的考试！')

    session['questions'] = [q['id'] for q in selected]
    session['answers'] = {}
    session['student_name'] = student_name
    session['wrong_only'] = True
    return render_template('quiz.html', questions=selected, enumerate=enumerate, get_source=get_source, student_name=student_name)


@app.route('/submit', methods=['POST'])
def submit():
    question_ids = session.get('questions', [])
    if not question_ids:
        return redirect(url_for('index'))

    user_answers = {}
    for qid in question_ids:
        key = f'q{qid}'
        user_answers[str(qid)] = request.form.get(key, '')

    session['answers'] = user_answers

    id_to_q = {q['id']: q for q in QUESTIONS}
    correct_count = 0
    results = []
    answer_records = []

    for qid in question_ids:
        q = id_to_q.get(qid)
        if not q:
            continue
        user_ans = user_answers.get(str(qid), '')
        is_correct = user_ans.upper() == q['answer'].upper()
        if is_correct:
            correct_count += 1
        results.append({
            'question': q,
            'user_answer': user_ans,
            'is_correct': is_correct,
        })
        answer_records.append((qid, user_ans, is_correct))

    total = len(question_ids)
    accuracy = round(correct_count / total * 100, 1) if total > 0 else 0

    student_name = session.get('student_name', '')
    exam_id = save_exam(student_name, total, correct_count, accuracy, answer_records)

    return render_template('result.html',
                           results=results,
                           correct_count=correct_count,
                           total=total,
                           accuracy=accuracy,
                           get_source=get_source,
                           exam_id=exam_id)


@app.route('/history')
def history():
    student_name = request.args.get('student', '').strip()
    exams = get_exam_list(limit=50, student_name=student_name if student_name else None)
    students = get_all_students()
    return render_template('history.html', exams=exams, students=students, current_student=student_name)


@app.route('/exam/<int:exam_id>')
def exam_detail(exam_id):
    data = get_exam_detail(exam_id)
    if not data:
        return redirect(url_for('history'))

    id_to_q = {q['id']: q for q in QUESTIONS}
    exam = data['exam']
    answers = data['answers']

    results = []
    for a in answers:
        q = id_to_q.get(a['question_id'])
        if not q:
            continue
        results.append({
            'question': q,
            'user_answer': a['user_answer'],
            'is_correct': bool(a['is_correct']),
        })

    return render_template('exam_detail.html',
                           exam=exam,
                           results=results,
                           get_source=get_source)


@app.route('/leaderboard')
def leaderboard():
    score_board = get_score_leaderboard(limit=20)
    total_board = get_total_leaderboard(limit=20)
    return render_template('leaderboard.html', score_board=score_board, total_board=total_board)


if __name__ == '__main__':
    app.run(debug=True, port=8080)
