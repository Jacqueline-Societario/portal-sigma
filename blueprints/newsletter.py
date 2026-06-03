"""
blueprints/newsletter.py — Informativos do Departamento Societário
Gestora (societario1) cria informativos; todas as colaboradoras leem.
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from blueprints.auth import login_obrigatorio
import database

newsletter_bp = Blueprint('newsletter', __name__, url_prefix='/newsletter')


def _is_admin():
    user = database.get_user_by_id(session.get('user_id'))
    return user and user['is_admin']


# ─── Rotas ────────────────────────────────────────────────────────────────────

@newsletter_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    search = request.args.get('search', '').strip()
    conn = database.get_db()
    if search:
        posts = conn.execute('''
            SELECT n.*, u.nome as autor_nome
            FROM newsletter_posts n
            LEFT JOIN users u ON n.autor_id = u.id
            WHERE n.publicado = 1
              AND (n.titulo LIKE ? OR n.conteudo LIKE ?)
            ORDER BY n.criado_em DESC
        ''', (f'%{search}%', f'%{search}%')).fetchall()
    else:
        posts = conn.execute('''
            SELECT n.*, u.nome as autor_nome
            FROM newsletter_posts n
            LEFT JOIN users u ON n.autor_id = u.id
            WHERE n.publicado = 1
            ORDER BY n.criado_em DESC
        ''').fetchall()
    conn.close()
    return render_template('newsletter/index.html', posts=posts, is_admin=_is_admin(), search=search)


@newsletter_bp.route('/novo', methods=['GET', 'POST'])
def novo():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    if not _is_admin():
        return redirect(url_for('newsletter.index'))

    erro = None
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        conteudo = request.form.get('conteudo', '').strip()
        publicado = 1 if request.form.get('publicado') else 0
        if not titulo or not conteudo:
            erro = 'Título e conteúdo são obrigatórios.'
        else:
            conn = database.get_db()
            cur = conn.execute(
                'INSERT INTO newsletter_posts (titulo, conteudo, autor_id, publicado) VALUES (?,?,?,?)',
                (titulo, conteudo, session['user_id'], publicado)
            )
            post_id = cur.lastrowid
            conn.commit()
            conn.close()
            if publicado:
                database.criar_notificacoes_para_evento(
                    modulo='newsletter',
                    tipo_evento='newsletter_novo',
                    titulo=f'Novo informativo publicado — {titulo}',
                    link_destino=f'/newsletter/{post_id}',
                        )
            return redirect(url_for('newsletter.ver', post_id=post_id))

    return render_template('newsletter/form.html', erro=erro, post=None)


@newsletter_bp.route('/<int:post_id>')
def ver(post_id):
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    conn = database.get_db()
    post = conn.execute('''
        SELECT n.*, u.nome as autor_nome
        FROM newsletter_posts n
        LEFT JOIN users u ON n.autor_id = u.id
        WHERE n.id = ?
    ''', (post_id,)).fetchone()
    conn.close()
    if not post:
        return redirect(url_for('newsletter.index'))
    return render_template('newsletter/ver.html', post=post, is_admin=_is_admin())


@newsletter_bp.route('/<int:post_id>/editar', methods=['GET', 'POST'])
def editar(post_id):
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    if not _is_admin():
        return redirect(url_for('newsletter.index'))

    conn = database.get_db()
    post = conn.execute('SELECT * FROM newsletter_posts WHERE id=?', (post_id,)).fetchone()
    conn.close()
    if not post:
        return redirect(url_for('newsletter.index'))

    erro = None
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        conteudo = request.form.get('conteudo', '').strip()
        publicado = 1 if request.form.get('publicado') else 0
        if not titulo or not conteudo:
            erro = 'Título e conteúdo são obrigatórios.'
        else:
            conn = database.get_db()
            conn.execute(
                'UPDATE newsletter_posts SET titulo=?, conteudo=?, publicado=? WHERE id=?',
                (titulo, conteudo, publicado, post_id)
            )
            conn.commit()
            conn.close()
            if publicado:
                database.criar_notificacoes_para_evento(
                    modulo='newsletter',
                    tipo_evento='newsletter_editado',
                    titulo=f'Informativo atualizado — {titulo}',
                    link_destino=f'/newsletter/{post_id}',
                        )
            return redirect(url_for('newsletter.ver', post_id=post_id))

    return render_template('newsletter/form.html', erro=erro, post=post)


@newsletter_bp.route('/<int:post_id>/excluir', methods=['POST'])
def excluir(post_id):
    if login_obrigatorio() or not _is_admin():
        return redirect(url_for('newsletter.index'))
    conn = database.get_db()
    conn.execute('DELETE FROM newsletter_posts WHERE id=?', (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('newsletter.index'))
