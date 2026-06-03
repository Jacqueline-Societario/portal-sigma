"""
database.py — Portal Societário Sigma
Gerencia o banco SQLite: usuários, manuais.
"""
import os
import sqlite3
import random
import string
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Tabela de usuários
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        ativo INTEGER DEFAULT 1,
        primeiro_acesso INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Tabela de manuais/conhecimentos
    cur.execute('''CREATE TABLE IF NOT EXISTS manuais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        categoria TEXT DEFAULT 'Geral',
        conteudo TEXT NOT NULL,
        criado_por INTEGER,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (criado_por) REFERENCES users(id)
    )''')

    # Usuárias do departamento Societário
    # Senha inicial: Sigma@2025 — cada uma redefine no primeiro acesso
    usuarios_padrao = [
        ('Jacqueline Benedito',  'societario1@gsigma.com.br', 'Sigma@2025'),
        ('Jaqueline Rodrigues',  'societario2@gsigma.com.br', 'Sigma@2025'),
        ('Beatriz',              'societario3@gsigma.com.br', 'Sigma@2025'),
        ('Jessica',              'societario4@gsigma.com.br', 'Sigma@2025'),
    ]
    for nome, email, senha in usuarios_padrao:
        cur.execute(
            'INSERT OR IGNORE INTO users (nome, email, senha_hash, primeiro_acesso) VALUES (?, ?, ?, 1)',
            (nome, email, generate_password_hash(senha))
        )

    # Tabela de empresas (sincronizada da planilha Google Sheets)
    cur.execute('''CREATE TABLE IF NOT EXISTS empresas_planilha (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fluxo TEXT,
        cnpj_cpf TEXT,
        nome_empresa TEXT NOT NULL,
        atuacao TEXT,
        escritorio TEXT,
        municipio TEXT,
        visa TEXT,
        cnes TEXT,
        venc_bombeiro TEXT,
        prot_bombeiro TEXT,
        licenca_ambiental TEXT,
        alvara_funcionamento TEXT,
        publicidade TEXT,
        tpi TEXT,
        procuracao TEXT,
        motivo_inativa TEXT DEFAULT '',
        nome_normalizado TEXT DEFAULT '',
        cnpj_normalizado TEXT DEFAULT '',
        aba TEXT DEFAULT 'ATIVAS',
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Tabela de newsletter / informativos
    cur.execute('''CREATE TABLE IF NOT EXISTS newsletter_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        conteudo TEXT NOT NULL,
        autor_id INTEGER,
        publicado INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (autor_id) REFERENCES users(id)
    )''')

    # Tabela de códigos OTP (2FA e recuperação de senha)
    cur.execute('''CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        codigo TEXT NOT NULL,
        motivo TEXT DEFAULT '2fa',
        expira_em TEXT NOT NULL,
        usado INTEGER DEFAULT 0,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Adicionar coluna is_admin se necessário (migração inline)
    try:
        cur.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    except Exception:
        pass

    # Garantir que societario1 é admin
    cur.execute("UPDATE users SET is_admin=1 WHERE email='societario1@gsigma.com.br'")

    # Tabela de permissões por ferramenta
    cur.execute('''CREATE TABLE IF NOT EXISTS user_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tool TEXT NOT NULL,
        allowed INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, tool)
    )''')

    # Tabela de log de atividade
    cur.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tool TEXT NOT NULL,
        action TEXT DEFAULT 'acesso',
        ip TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── Movimentação de Empresas ───────────────────────────────────────────────

    # Registros de entrada e saída de empresas (alimentado via e-mail)
    cur.execute('''CREATE TABLE IF NOT EXISTS movimentacao_empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL,
        razao_social TEXT DEFAULT '',
        codigo_dominio TEXT DEFAULT '',
        primeira_competencia TEXT DEFAULT '',
        grupo TEXT DEFAULT '',
        contatos TEXT DEFAULT '[]',
        nome_empresa TEXT DEFAULT '',
        fim_competencia TEXT DEFAULT '',
        motivo TEXT DEFAULT '',
        notificado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # IDs de e-mails já processados (evitar reprocessamento)
    cur.execute('''CREATE TABLE IF NOT EXISTS emails_processados (
        gmail_message_id TEXT PRIMARY KEY,
        processado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Log de verificações de e-mail
    cur.execute('''CREATE TABLE IF NOT EXISTS email_check_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        verificado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        novos INTEGER DEFAULT 0
    )''')

    # Tabela de notificações do sino
    cur.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tipo_evento TEXT NOT NULL,
        modulo TEXT NOT NULL,
        titulo TEXT NOT NULL,
        descricao TEXT DEFAULT '',
        link_destino TEXT DEFAULT '',
        lida INTEGER DEFAULT 0,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_leitura TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── Passkeys / WebAuthn ────────────────────────────────────────────────────

    cur.execute('''CREATE TABLE IF NOT EXISTS webauthn_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        credential_id TEXT NOT NULL UNIQUE,
        public_key TEXT NOT NULL,
        sign_count INTEGER DEFAULT 0,
        name TEXT DEFAULT 'Minha passkey',
        aaguid TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── Dispositivos Confiáveis ────────────────────────────────────────────────

    cur.execute('''CREATE TABLE IF NOT EXISTS trusted_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        device_token TEXT NOT NULL UNIQUE,
        device_name TEXT DEFAULT '',
        ip TEXT DEFAULT '',
        user_agent TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT NOT NULL,
        revoked INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── Log de Segurança ──────────────────────────────────────────────────────

    cur.execute('''CREATE TABLE IF NOT EXISTS security_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT NOT NULL,
        ip TEXT DEFAULT '',
        user_agent TEXT DEFAULT '',
        details TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── Tentativas falhas (rate limit) ────────────────────────────────────────

    cur.execute('''CREATE TABLE IF NOT EXISTS failed_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        user_id INTEGER,
        attempt_type TEXT DEFAULT 'login',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── Processos de Formulários (Google Forms) ────────────────────────────────

    cur.execute('''CREATE TABLE IF NOT EXISTS formularios_cadastrados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo_processo TEXT NOT NULL,
        link_formulario TEXT DEFAULT '',
        form_id TEXT DEFAULT '',
        sheet_id TEXT DEFAULT '',
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS processos_formularios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        formulario_id INTEGER,
        form_name TEXT NOT NULL,
        tipo_processo TEXT DEFAULT '',
        response_id TEXT UNIQUE,
        link_resposta TEXT DEFAULT '',
        enviado_por TEXT DEFAULT '',
        data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Novo',
        responsavel_id INTEGER,
        observacoes TEXT DEFAULT '',
        observacoes_atualizadas_em TIMESTAMP,
        observacoes_atualizadas_por INTEGER,
        arquivado INTEGER DEFAULT 0,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (formulario_id) REFERENCES formularios_cadastrados(id),
        FOREIGN KEY (responsavel_id) REFERENCES users(id),
        FOREIGN KEY (observacoes_atualizadas_por) REFERENCES users(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS processos_form_respostas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        processo_id INTEGER NOT NULL,
        pergunta TEXT NOT NULL,
        resposta TEXT DEFAULT '',
        ordem INTEGER DEFAULT 0,
        FOREIGN KEY (processo_id) REFERENCES processos_formularios(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS anotacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        titulo TEXT DEFAULT '',
        conteudo TEXT DEFAULT '',
        cor TEXT DEFAULT 'amarelo',
        pos_x INTEGER DEFAULT 20,
        pos_y INTEGER DEFAULT 20,
        largura INTEGER DEFAULT 320,
        altura INTEGER DEFAULT 260,
        ordem INTEGER DEFAULT 0,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND ativo = 1', (email,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ? AND ativo = 1', (user_id,)).fetchone()
    conn.close()
    return user


def atualizar_senha(user_id, nova_senha_hash):
    conn = get_db()
    conn.execute(
        'UPDATE users SET senha_hash = ?, primeiro_acesso = 0 WHERE id = ?',
        (nova_senha_hash, user_id)
    )
    # Revogar dispositivos confiáveis após troca de senha (segurança)
    try:
        conn.execute('UPDATE trusted_devices SET revoked=1 WHERE user_id=?', (user_id,))
    except Exception:
        pass  # tabela pode não existir ainda em instâncias antigas
    conn.commit()
    conn.close()


def add_coluna_se_necessario():
    """Migração: adiciona colunas novas se o banco já existia."""
    conn = get_db()
    cur = conn.cursor()
    migracoes = [
        'ALTER TABLE users ADD COLUMN primeiro_acesso INTEGER DEFAULT 1',
        'ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0',
        '''CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tool TEXT NOT NULL,
            allowed INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, tool)
        )''',
        '''CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tool TEXT NOT NULL,
            action TEXT DEFAULT \'acesso\',
            ip TEXT DEFAULT \'\',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
        'ALTER TABLE empresas_planilha ADD COLUMN motivo_inativa TEXT DEFAULT ""',
        'ALTER TABLE empresas_planilha ADD COLUMN nome_normalizado TEXT DEFAULT ""',
        'ALTER TABLE empresas_planilha ADD COLUMN cnpj_normalizado TEXT DEFAULT ""',
        '''CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            motivo TEXT DEFAULT \'2fa\',
            expira_em TEXT NOT NULL,
            usado INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
        'ALTER TABLE movimentacao_empresas ADD COLUMN email_data TIMESTAMP',
        'ALTER TABLE empresas_planilha ADD COLUMN codigo_dominio TEXT DEFAULT ""',
        'ALTER TABLE empresas_planilha ADD COLUMN editado_em TIMESTAMP',
        'ALTER TABLE empresas_planilha ADD COLUMN editado_por TEXT DEFAULT ""',
        'ALTER TABLE empresas_planilha ADD COLUMN responsavel TEXT DEFAULT ""',
        'ALTER TABLE empresas_planilha ADD COLUMN observacoes TEXT DEFAULT ""',
        'ALTER TABLE empresas_planilha ADD COLUMN certificado_digital TEXT DEFAULT ""',
        '''CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            credential_id TEXT NOT NULL UNIQUE,
            public_key TEXT NOT NULL,
            sign_count INTEGER DEFAULT 0,
            name TEXT DEFAULT \'Minha passkey\',
            aaguid TEXT DEFAULT \'\',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS trusted_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_token TEXT NOT NULL UNIQUE,
            device_name TEXT DEFAULT \'\',
            ip TEXT DEFAULT \'\',
            user_agent TEXT DEFAULT \'\',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            revoked INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            ip TEXT DEFAULT \'\',
            user_agent TEXT DEFAULT \'\',
            details TEXT DEFAULT \'\',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS failed_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            user_id INTEGER,
            attempt_type TEXT DEFAULT \'login\',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tipo_evento TEXT NOT NULL,
            modulo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT DEFAULT \'\',
            link_destino TEXT DEFAULT \'\',
            lida INTEGER DEFAULT 0,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_leitura TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS formularios_cadastrados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo_processo TEXT NOT NULL,
            link_formulario TEXT DEFAULT \'\',
            form_id TEXT DEFAULT \'\',
            sheet_id TEXT DEFAULT \'\',
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS processos_formularios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formulario_id INTEGER,
            form_name TEXT NOT NULL,
            tipo_processo TEXT DEFAULT \'\',
            response_id TEXT UNIQUE,
            link_resposta TEXT DEFAULT \'\',
            enviado_por TEXT DEFAULT \'\',
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT \'Novo\',
            responsavel_id INTEGER,
            observacoes TEXT DEFAULT \'\',
            observacoes_atualizadas_em TIMESTAMP,
            observacoes_atualizadas_por INTEGER,
            arquivado INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (formulario_id) REFERENCES formularios_cadastrados(id),
            FOREIGN KEY (responsavel_id) REFERENCES users(id),
            FOREIGN KEY (observacoes_atualizadas_por) REFERENCES users(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS processos_form_respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_id INTEGER NOT NULL,
            pergunta TEXT NOT NULL,
            resposta TEXT DEFAULT \'\',
            ordem INTEGER DEFAULT 0,
            FOREIGN KEY (processo_id) REFERENCES processos_formularios(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS anotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            titulo TEXT DEFAULT \'\',
            conteudo TEXT DEFAULT \'\',
            cor TEXT DEFAULT \'amarelo\',
            pos_x INTEGER DEFAULT 20,
            pos_y INTEGER DEFAULT 20,
            largura INTEGER DEFAULT 320,
            altura INTEGER DEFAULT 260,
            ordem INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
    ]
    for sql in migracoes:
        try:
            cur.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


def listar_manuais(categoria=None, search=None):
    conn = get_db()
    if search:
        like = f'%{search}%'
        rows = conn.execute(
            '''SELECT m.*, u.nome as autor FROM manuais m
               LEFT JOIN users u ON m.criado_por = u.id
               WHERE (m.titulo LIKE ? OR m.conteudo LIKE ?)
               ORDER BY m.categoria, m.titulo''',
            (like, like)
        ).fetchall()
    elif categoria:
        rows = conn.execute(
            '''SELECT m.*, u.nome as autor FROM manuais m
               LEFT JOIN users u ON m.criado_por = u.id
               WHERE m.categoria = ? ORDER BY m.atualizado_em DESC''',
            (categoria,)
        ).fetchall()
    else:
        rows = conn.execute(
            '''SELECT m.*, u.nome as autor FROM manuais m
               LEFT JOIN users u ON m.criado_por = u.id
               ORDER BY m.categoria, m.titulo'''
        ).fetchall()
    conn.close()
    return rows


def get_manual(manual_id):
    conn = get_db()
    row = conn.execute(
        '''SELECT m.*, u.nome as autor FROM manuais m
           LEFT JOIN users u ON m.criado_por = u.id
           WHERE m.id = ?''',
        (manual_id,)
    ).fetchone()
    conn.close()
    return row


def criar_manual(titulo, categoria, conteudo, user_id):
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO manuais (titulo, categoria, conteudo, criado_por) VALUES (?, ?, ?, ?)',
        (titulo, categoria, conteudo, user_id)
    )
    manual_id = cur.lastrowid
    conn.commit()
    conn.close()
    return manual_id


def atualizar_manual(manual_id, titulo, categoria, conteudo):
    conn = get_db()
    conn.execute(
        '''UPDATE manuais SET titulo=?, categoria=?, conteudo=?,
           atualizado_em=CURRENT_TIMESTAMP WHERE id=?''',
        (titulo, categoria, conteudo, manual_id)
    )
    conn.commit()
    conn.close()


def deletar_manual(manual_id):
    conn = get_db()
    conn.execute('DELETE FROM manuais WHERE id=?', (manual_id,))
    conn.commit()
    conn.close()


# ── OTP (códigos de verificação) ──────────────────────────────────────────────

def criar_otp(user_id: int, motivo: str = '2fa') -> str:
    """Gera código de 6 dígitos, invalida anteriores do mesmo usuário/motivo e salva."""
    codigo = ''.join(random.choices(string.digits, k=6))
    expira = (datetime.utcnow() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    # Invalida códigos anteriores do mesmo motivo
    conn.execute(
        'UPDATE otp_codes SET usado=1 WHERE user_id=? AND motivo=? AND usado=0',
        (user_id, motivo)
    )
    conn.execute(
        'INSERT INTO otp_codes (user_id, codigo, motivo, expira_em) VALUES (?, ?, ?, ?)',
        (user_id, codigo, motivo, expira)
    )
    conn.commit()
    conn.close()
    return codigo


def verificar_otp(user_id: int, codigo: str, motivo: str = '2fa') -> bool:
    """Verifica se o código é válido (correto, não expirado, não usado). Marca como usado."""
    conn = get_db()
    agora = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    row = conn.execute(
        '''SELECT id FROM otp_codes
           WHERE user_id=? AND codigo=? AND motivo=? AND usado=0 AND expira_em > ?
           ORDER BY id DESC LIMIT 1''',
        (user_id, codigo, motivo, agora)
    ).fetchone()
    if row:
        conn.execute('UPDATE otp_codes SET usado=1 WHERE id=?', (row['id'],))
        conn.commit()
    conn.close()
    return row is not None


# ── Permissões por ferramenta ──────────────────────────────────────────────────

# Ferramentas disponíveis no portal
TOOLS = {
    'contrato':         'Elaboração de Contrato Social',
    'procuracoes':      'Elaboração de Procurações',
    'declaracoes':      'Elaboração de Declarações',
    'manuais':          'Área de Conhecimentos',
    'empresas':         'Consulta de Empresas',
    'empresas_editar':  'Edição de Empresas',
    'newsletter':       'Informativos',
    'conferencia':      'Conferência de Contrato',
    'movimentacao':     'Movimentação de Empresas',
    'cnae':             'Consulta CNAE / Regime Tributário',
}


def get_user_permission(user_id: int, tool: str) -> bool:
    """Retorna True se o usuário tem acesso à ferramenta (padrão: True)."""
    conn = get_db()
    row = conn.execute(
        'SELECT allowed FROM user_permissions WHERE user_id=? AND tool=?',
        (user_id, tool)
    ).fetchone()
    conn.close()
    # Se não há registro, acesso liberado por padrão
    return bool(row['allowed']) if row else True


def set_user_permission(user_id: int, tool: str, allowed: bool):
    """Define permissão de um usuário para uma ferramenta."""
    conn = get_db()
    conn.execute(
        '''INSERT INTO user_permissions (user_id, tool, allowed, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id, tool) DO UPDATE SET allowed=excluded.allowed, updated_at=CURRENT_TIMESTAMP''',
        (user_id, tool, 1 if allowed else 0)
    )
    conn.commit()
    conn.close()


def get_all_permissions() -> dict:
    """Retorna dict {user_id: {tool: allowed}} para todos os usuários e ferramentas."""
    conn = get_db()
    rows = conn.execute('SELECT user_id, tool, allowed FROM user_permissions').fetchall()
    conn.close()
    result = {}
    for row in rows:
        uid = row['user_id']
        if uid not in result:
            result[uid] = {}
        result[uid][row['tool']] = bool(row['allowed'])
    return result


def get_all_users_active():
    """Lista todos os usuários ativos."""
    conn = get_db()
    rows = conn.execute(
        'SELECT id, nome, email, is_admin, criado_em FROM users WHERE ativo=1 ORDER BY nome'
    ).fetchall()
    conn.close()
    return rows


def get_all_users():
    """Lista TODOS os usuários (ativos e inativos), para gerenciamento admin."""
    conn = get_db()
    rows = conn.execute(
        'SELECT id, nome, email, is_admin, ativo, criado_em FROM users ORDER BY ativo DESC, nome'
    ).fetchall()
    conn.close()
    return rows


def criar_usuario(nome: str, email: str) -> dict:
    """
    Cria novo usuário com senha padrão Sigma@2025 (primeiro_acesso=1).
    Retorna {'ok': True, 'id': user_id} ou {'ok': False, 'erro': msg}.
    """
    email = email.strip().lower()
    nome = nome.strip()
    if not nome or not email:
        return {'ok': False, 'erro': 'Nome e e-mail são obrigatórios'}
    conn = get_db()
    # Verificar duplicidade (incluindo inativos)
    existe = conn.execute(
        'SELECT id, ativo FROM users WHERE email = ?', (email,)
    ).fetchone()
    if existe:
        conn.close()
        if existe['ativo']:
            return {'ok': False, 'erro': 'E-mail já cadastrado'}
        else:
            return {'ok': False, 'erro': 'E-mail já existe (usuário inativo — use "Reativar")'}
    senha_hash = generate_password_hash('Sigma@2025')
    cur = conn.execute(
        'INSERT INTO users (nome, email, senha_hash, ativo, primeiro_acesso) VALUES (?, ?, ?, 1, 1)',
        (nome, email, senha_hash)
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {'ok': True, 'id': user_id}


def editar_usuario(user_id: int, nome: str) -> dict:
    """Atualiza nome do usuário. Retorna {'ok': True} ou {'ok': False, 'erro': msg}."""
    nome = nome.strip()
    if not nome:
        return {'ok': False, 'erro': 'Nome não pode ser vazio'}
    conn = get_db()
    conn.execute('UPDATE users SET nome = ? WHERE id = ?', (nome, user_id))
    conn.commit()
    conn.close()
    return {'ok': True}


def toggle_usuario_ativo(user_id: int, ativo: bool) -> dict:
    """Ativa ou inativa um usuário. Admin não pode ser inativado."""
    conn = get_db()
    user = conn.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return {'ok': False, 'erro': 'Usuário não encontrado'}
    if user['is_admin'] and not ativo:
        conn.close()
        return {'ok': False, 'erro': 'A administradora não pode ser inativada'}
    conn.execute('UPDATE users SET ativo = ? WHERE id = ?', (1 if ativo else 0, user_id))
    conn.commit()
    conn.close()
    return {'ok': True}


def excluir_usuario(user_id: int) -> dict:
    """Remove permanentemente um usuário. Admin não pode ser excluído."""
    conn = get_db()
    user = conn.execute('SELECT is_admin, email FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return {'ok': False, 'erro': 'Usuário não encontrado'}
    if user['is_admin']:
        conn.close()
        return {'ok': False, 'erro': 'A administradora não pode ser excluída'}
    # Limpar permissões associadas
    conn.execute('DELETE FROM user_permissions WHERE user_id = ?', (user_id,))
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return {'ok': True}


def redefinir_senha_usuario(user_id: int) -> dict:
    """Redefine senha do usuário para Sigma@2025 e força troca no próximo acesso."""
    conn = get_db()
    user = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return {'ok': False, 'erro': 'Usuário não encontrado'}
    senha_hash = generate_password_hash('Sigma@2025')
    conn.execute(
        'UPDATE users SET senha_hash = ?, primeiro_acesso = 1 WHERE id = ?',
        (senha_hash, user_id)
    )
    conn.commit()
    conn.close()
    return {'ok': True}


# ── Log de atividade ──────────────────────────────────────────────────────────

def log_activity(user_id: int, tool: str, action: str = 'acesso', ip: str = ''):
    """Registra acesso de um usuário a uma ferramenta."""
    conn = get_db()
    conn.execute(
        'INSERT INTO activity_log (user_id, tool, action, ip) VALUES (?, ?, ?, ?)',
        (user_id, tool, action, ip)
    )
    conn.commit()
    conn.close()


def get_activity_summary(limit: int = 100) -> list:
    """Retorna log de atividade recente com nome do usuário."""
    conn = get_db()
    rows = conn.execute(
        '''SELECT a.created_at, u.nome, u.email, a.tool, a.action, a.ip
           FROM activity_log a
           JOIN users u ON a.user_id = u.id
           ORDER BY a.created_at DESC LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return rows


def get_last_access_per_user() -> dict:
    """Retorna {user_id: {tool: last_access_timestamp}} — último acesso por usuário/ferramenta."""
    conn = get_db()
    rows = conn.execute(
        '''SELECT user_id, tool, MAX(created_at) as last_at
           FROM activity_log GROUP BY user_id, tool'''
    ).fetchall()
    conn.close()
    result = {}
    for row in rows:
        uid = row['user_id']
        if uid not in result:
            result[uid] = {}
        result[uid][row['tool']] = row['last_at']
    return result


# ── Empresas — Edição e Criação ───────────────────────────────────────────────

def criar_empresa(campos: dict, criado_por: str = '') -> int:
    """Insere uma nova empresa manualmente no banco local."""
    import unicodedata, re

    def _normalizar(s):
        if not s:
            return ''
        nfkd = unicodedata.normalize('NFD', s.lower())
        return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')

    def _normalizar_cnpj(s):
        return re.sub(r'[.\-/\s]', '', s.strip()) if s else ''

    conn = get_db()
    conn.execute(
        '''INSERT INTO empresas_planilha
           (fluxo, cnpj_cpf, nome_empresa, atuacao, escritorio, municipio,
            visa, cnes, venc_bombeiro, prot_bombeiro, licenca_ambiental,
            alvara_funcionamento, publicidade, tpi, procuracao,
            motivo_inativa, nome_normalizado, cnpj_normalizado,
            codigo_dominio, aba, atualizado_em, editado_em, editado_por, observacoes, certificado_digital)
           VALUES ('',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,?,?,?)''',
        (
            campos.get('cnpj_cpf', ''),
            campos.get('nome_empresa', ''),
            campos.get('atuacao', ''),
            campos.get('escritorio', ''),
            campos.get('municipio', ''),
            campos.get('visa', ''),
            campos.get('cnes', ''),
            campos.get('venc_bombeiro', ''),
            campos.get('prot_bombeiro', ''),
            campos.get('licenca_ambiental', ''),
            campos.get('alvara_funcionamento', ''),
            campos.get('publicidade', ''),
            campos.get('tpi', ''),
            campos.get('procuracao', ''),
            campos.get('motivo_inativa', ''),
            _normalizar(campos.get('nome_empresa', '')),
            _normalizar_cnpj(campos.get('cnpj_cpf', '')),
            campos.get('codigo_dominio', ''),
            campos.get('aba', 'ATIVAS'),
            criado_por,
            campos.get('observacoes', ''),
            campos.get('certificado_digital', ''),
        )
    )
    empresa_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return empresa_id


def update_empresa(empresa_id: int, campos: dict, editado_por: str = ''):
    """Atualiza campos de uma empresa no banco local."""
    import unicodedata, re

    def _normalizar(s):
        if not s:
            return ''
        nfkd = unicodedata.normalize('NFD', s.lower())
        return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')

    def _normalizar_cnpj(s):
        return re.sub(r'[.\-/\s]', '', s.strip()) if s else ''

    # Campos editáveis
    editaveis = [
        'fluxo', 'cnpj_cpf', 'nome_empresa', 'atuacao', 'escritorio', 'municipio',
        'visa', 'cnes', 'venc_bombeiro', 'prot_bombeiro', 'licenca_ambiental',
        'alvara_funcionamento', 'publicidade', 'tpi', 'procuracao',
        'motivo_inativa', 'aba', 'codigo_dominio', 'observacoes', 'responsavel',
        'certificado_digital',
    ]
    sets = []
    params = []
    for campo in editaveis:
        if campo in campos:
            sets.append(f'{campo} = ?')
            params.append(campos[campo])

    if not sets:
        return False

    # Recalcular campos normalizados se nome ou cnpj mudaram
    if 'nome_empresa' in campos:
        sets.append('nome_normalizado = ?')
        params.append(_normalizar(campos['nome_empresa']))
    if 'cnpj_cpf' in campos:
        sets.append('cnpj_normalizado = ?')
        params.append(_normalizar_cnpj(campos['cnpj_cpf']))

    sets.append('editado_em = CURRENT_TIMESTAMP')
    sets.append('editado_por = ?')
    params.append(editado_por)
    params.append(empresa_id)

    conn = get_db()
    conn.execute(
        f'UPDATE empresas_planilha SET {", ".join(sets)} WHERE id = ?',
        params
    )
    conn.commit()
    conn.close()
    return True


# ── Movimentação de Empresas ──────────────────────────────────────────────────

def email_ja_processado(gmail_message_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        'SELECT 1 FROM emails_processados WHERE gmail_message_id=?', (gmail_message_id,)
    ).fetchone()
    conn.close()
    return row is not None


def marcar_email_processado(gmail_message_id: str):
    conn = get_db()
    conn.execute(
        'INSERT OR IGNORE INTO emails_processados (gmail_message_id) VALUES (?)',
        (gmail_message_id,)
    )
    conn.commit()
    conn.close()


def salvar_movimentacao(tipo: str, **campos):
    conn = get_db()
    conn.execute(
        '''INSERT INTO movimentacao_empresas
           (tipo, razao_social, codigo_dominio, primeira_competencia,
            grupo, contatos, nome_empresa, fim_competencia, motivo, email_data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            tipo,
            campos.get('razao_social', ''),
            campos.get('codigo_dominio', ''),
            campos.get('primeira_competencia', ''),
            campos.get('grupo', ''),
            campos.get('contatos', '[]'),
            campos.get('nome_empresa', ''),
            campos.get('fim_competencia', ''),
            campos.get('motivo', ''),
            campos.get('email_data', None),
        )
    )
    conn.commit()
    conn.close()


def get_movimentacoes(tipo: str) -> list:
    """
    Retorna movimentações dos últimos 3 meses com lógica de cruzamento:
    - Entrada só aparece se não há saída mais recente para o mesmo código domínio.
    - Saída só aparece se não há entrada mais recente para o mesmo código domínio.
    - Deduplicação: apenas o registro mais recente por empresa.
    """
    conn = get_db()

    if tipo == 'entrada':
        rows = conn.execute('''
            WITH mais_recentes AS (
                -- Registro mais recente por razao_social
                SELECT MAX(id) AS id
                FROM movimentacao_empresas
                WHERE tipo = 'entrada'
                  AND notificado_em >= datetime('now', '-3 months')
                GROUP BY razao_social
            ),
            saidas_recentes AS (
                -- Saída mais recente por código domínio (últimos 3 meses)
                SELECT codigo_dominio, MAX(notificado_em) AS ultima_saida
                FROM movimentacao_empresas
                WHERE tipo = 'saida'
                  AND notificado_em >= datetime('now', '-3 months')
                  AND codigo_dominio != ''
                GROUP BY codigo_dominio
            )
            SELECT e.*
            FROM movimentacao_empresas e
            JOIN mais_recentes mr ON e.id = mr.id
            LEFT JOIN saidas_recentes sr
                   ON sr.codigo_dominio = e.codigo_dominio
                  AND e.codigo_dominio != ''
            WHERE sr.codigo_dominio IS NULL          -- sem saída correspondente
               OR sr.ultima_saida < e.notificado_em  -- entrada é mais recente que a saída
            ORDER BY COALESCE(e.email_data, e.notificado_em) DESC
        ''').fetchall()

    else:  # saida
        rows = conn.execute('''
            WITH mais_recentes AS (
                -- Registro mais recente por código domínio (ou nome_empresa se sem código)
                SELECT MAX(id) AS id
                FROM movimentacao_empresas
                WHERE tipo = 'saida'
                  AND notificado_em >= datetime('now', '-3 months')
                GROUP BY CASE WHEN codigo_dominio != '' THEN codigo_dominio ELSE nome_empresa END
            ),
            entradas_recentes AS (
                -- Entrada mais recente por código domínio (últimos 3 meses)
                SELECT codigo_dominio, MAX(notificado_em) AS ultima_entrada
                FROM movimentacao_empresas
                WHERE tipo = 'entrada'
                  AND notificado_em >= datetime('now', '-3 months')
                  AND codigo_dominio != ''
                GROUP BY codigo_dominio
            )
            SELECT s.*
            FROM movimentacao_empresas s
            JOIN mais_recentes mr ON s.id = mr.id
            LEFT JOIN entradas_recentes er
                   ON er.codigo_dominio = s.codigo_dominio
                  AND s.codigo_dominio != ''
            WHERE er.codigo_dominio IS NULL           -- sem entrada correspondente
               OR er.ultima_entrada < s.notificado_em -- saída é mais recente que a entrada
            ORDER BY COALESCE(s.email_data, s.notificado_em) DESC
        ''').fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_ultima_verificacao_email() -> str:
    conn = get_db()
    row = conn.execute(
        'SELECT verificado_em, novos FROM email_check_log ORDER BY id DESC LIMIT 1'
    ).fetchone()
    conn.close()
    if row:
        return {'verificado_em': row['verificado_em'], 'novos': row['novos']}
    return None


def registrar_verificacao_email(novos: int = 0):
    conn = get_db()
    conn.execute(
        'INSERT INTO email_check_log (novos) VALUES (?)', (novos,)
    )
    conn.commit()
    conn.close()


# ── Notificações ──────────────────────────────────────────────────────────────

def _criar_notificacao_user(user_id: int, tipo_evento: str, modulo: str,
                             titulo: str, descricao: str, link_destino: str):
    """Insere uma notificação individual para um usuário."""
    conn = get_db()
    conn.execute(
        '''INSERT INTO notifications
           (user_id, tipo_evento, modulo, titulo, descricao, link_destino)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, tipo_evento, modulo, titulo, descricao, link_destino)
    )
    conn.commit()
    conn.close()


def criar_notificacoes_para_evento(modulo: str, tipo_evento: str, titulo: str,
                                    descricao: str = '', link_destino: str = '',
                                    excluir_user_id: int = None):
    """
    Cria notificações para todos os usuários ativos com acesso ao módulo.
    excluir_user_id: não notifica quem gerou o evento.
    """
    conn = get_db()
    users = conn.execute('SELECT id FROM users WHERE ativo=1').fetchall()
    conn.close()
    for user in users:
        uid = user['id']
        if excluir_user_id and uid == excluir_user_id:
            continue
        if get_user_permission(uid, modulo):
            _criar_notificacao_user(uid, tipo_evento, modulo, titulo, descricao, link_destino)


def get_notificacoes(user_id: int) -> dict:
    """Retorna notificações não lidas + histórico de 60 dias para o usuário."""
    conn = get_db()
    nao_lidas = conn.execute(
        '''SELECT * FROM notifications WHERE user_id=? AND lida=0
           ORDER BY data_criacao DESC''',
        (user_id,)
    ).fetchall()
    lidas = conn.execute(
        '''SELECT * FROM notifications WHERE user_id=? AND lida=1
           AND data_criacao >= datetime('now', '-60 days')
           ORDER BY data_criacao DESC LIMIT 50''',
        (user_id,)
    ).fetchall()
    conn.close()
    return {
        'nao_lidas': [dict(r) for r in nao_lidas],
        'lidas': [dict(r) for r in lidas],
        'total_nao_lidas': len(nao_lidas),
    }


def marcar_notificacao_lida(notif_id: int, user_id: int):
    """Marca uma notificação específica como lida."""
    conn = get_db()
    conn.execute(
        '''UPDATE notifications SET lida=1, data_leitura=CURRENT_TIMESTAMP
           WHERE id=? AND user_id=?''',
        (notif_id, user_id)
    )
    conn.commit()
    conn.close()


def marcar_todas_lidas(user_id: int):
    """Marca todas as notificações não lidas do usuário como lidas."""
    conn = get_db()
    conn.execute(
        '''UPDATE notifications SET lida=1, data_leitura=CURRENT_TIMESTAMP
           WHERE user_id=? AND lida=0''',
        (user_id,)
    )
    conn.commit()
    conn.close()


def count_nao_lidas(user_id: int) -> int:
    """Retorna o total de notificações não lidas do usuário."""
    conn = get_db()
    row = conn.execute(
        'SELECT COUNT(*) FROM notifications WHERE user_id=? AND lida=0',
        (user_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


# ── WebAuthn / Passkeys ────────────────────────────────────────────────────────

def get_webauthn_credentials(user_id: int) -> list:
    """Lista todas as passkeys do usuário."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM webauthn_credentials WHERE user_id=? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_webauthn_credential_by_id(credential_id: str) -> dict:
    """Busca passkey pelo credential_id (base64url)."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM webauthn_credentials WHERE credential_id=?',
        (credential_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_webauthn_credential(user_id: int, credential_id: str, public_key: str,
                              sign_count: int, aaguid: str = '', name: str = 'Minha passkey') -> int:
    """Salva nova passkey no banco."""
    conn = get_db()
    cur = conn.execute(
        '''INSERT INTO webauthn_credentials
           (user_id, credential_id, public_key, sign_count, aaguid, name)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, credential_id, public_key, sign_count, aaguid, name)
    )
    cred_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cred_id


def update_webauthn_sign_count(credential_id: str, new_sign_count: int):
    """Atualiza sign_count e last_used_at após autenticação bem-sucedida."""
    conn = get_db()
    conn.execute(
        '''UPDATE webauthn_credentials
           SET sign_count=?, last_used_at=CURRENT_TIMESTAMP
           WHERE credential_id=?''',
        (new_sign_count, credential_id)
    )
    conn.commit()
    conn.close()


def rename_webauthn_credential(cred_id: int, user_id: int, name: str):
    """Renomeia uma passkey."""
    conn = get_db()
    conn.execute(
        'UPDATE webauthn_credentials SET name=? WHERE id=? AND user_id=?',
        (name, cred_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_webauthn_credential(cred_id: int, user_id: int):
    """Remove uma passkey do usuário."""
    conn = get_db()
    conn.execute(
        'DELETE FROM webauthn_credentials WHERE id=? AND user_id=?',
        (cred_id, user_id)
    )
    conn.commit()
    conn.close()


def count_webauthn_credentials(user_id: int) -> int:
    """Conta quantas passkeys o usuário tem cadastradas."""
    conn = get_db()
    row = conn.execute(
        'SELECT COUNT(*) FROM webauthn_credentials WHERE user_id=?',
        (user_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


# ── Dispositivos Confiáveis ────────────────────────────────────────────────────

def create_trusted_device(user_id: int, device_token: str, device_name: str,
                           ip: str, user_agent: str, expires_at: str):
    """Registra novo dispositivo confiável."""
    conn = get_db()
    conn.execute(
        '''INSERT OR REPLACE INTO trusted_devices
           (user_id, device_token, device_name, ip, user_agent, expires_at, revoked)
           VALUES (?, ?, ?, ?, ?, ?, 0)''',
        (user_id, device_token, device_name, ip, user_agent, expires_at)
    )
    conn.commit()
    conn.close()


def get_trusted_device_info(user_id: int, device_token: str) -> dict:
    """Retorna info do dispositivo confiável, ou None."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM trusted_devices WHERE user_id=? AND device_token=? AND revoked=0',
        (user_id, device_token)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_trusted_device_last_seen(device_token: str):
    """Atualiza last_seen_at do dispositivo."""
    conn = get_db()
    conn.execute(
        'UPDATE trusted_devices SET last_seen_at=CURRENT_TIMESTAMP WHERE device_token=?',
        (device_token,)
    )
    conn.commit()
    conn.close()


def revoke_all_trusted_devices(user_id: int):
    """Revoga todos os dispositivos confiáveis do usuário (ex: após troca de senha)."""
    conn = get_db()
    conn.execute(
        'UPDATE trusted_devices SET revoked=1 WHERE user_id=?',
        (user_id,)
    )
    conn.commit()
    conn.close()


def revoke_trusted_device(device_id: int, user_id: int):
    """Revoga um dispositivo confiável específico."""
    conn = get_db()
    conn.execute(
        'UPDATE trusted_devices SET revoked=1 WHERE id=? AND user_id=?',
        (device_id, user_id)
    )
    conn.commit()
    conn.close()


def list_trusted_devices(user_id: int) -> list:
    """Lista dispositivos confiáveis ativos do usuário."""
    conn = get_db()
    rows = conn.execute(
        '''SELECT * FROM trusted_devices WHERE user_id=? AND revoked=0
           ORDER BY last_seen_at DESC''',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Log de Segurança ──────────────────────────────────────────────────────────

def security_log(event_type: str, user_id: int = None, ip: str = '',
                  user_agent: str = '', details: str = ''):
    """Registra evento de segurança."""
    conn = get_db()
    conn.execute(
        '''INSERT INTO security_logs (user_id, event_type, ip, user_agent, details)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, event_type, ip, user_agent, details)
    )
    conn.commit()
    conn.close()


def get_security_logs(limit: int = 100) -> list:
    """Retorna logs de segurança recentes."""
    conn = get_db()
    rows = conn.execute(
        '''SELECT s.*, u.nome as user_nome, u.email as user_email
           FROM security_logs s
           LEFT JOIN users u ON s.user_id = u.id
           ORDER BY s.created_at DESC LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Tentativas Falhas (Rate Limit) ────────────────────────────────────────────

def record_failed_attempt(ip: str, user_id: int = None, attempt_type: str = 'login'):
    """Registra tentativa falha de login ou WebAuthn."""
    conn = get_db()
    conn.execute(
        'INSERT INTO failed_attempts (ip, user_id, attempt_type) VALUES (?, ?, ?)',
        (ip, user_id, attempt_type)
    )
    conn.commit()
    conn.close()


def count_failed_attempts(ip: str, user_id: int = None,
                           window_minutes: int = 15) -> int:
    """Conta tentativas falhas recentes de um IP (e opcionalmente de um user)."""
    conn = get_db()
    since = (datetime.utcnow() - timedelta(minutes=window_minutes)).strftime('%Y-%m-%d %H:%M:%S')
    if user_id:
        row = conn.execute(
            '''SELECT COUNT(*) FROM failed_attempts
               WHERE (ip=? OR user_id=?) AND created_at > ?''',
            (ip, user_id, since)
        ).fetchone()
    else:
        row = conn.execute(
            'SELECT COUNT(*) FROM failed_attempts WHERE ip=? AND created_at > ?',
            (ip, since)
        ).fetchone()
    conn.close()
    return row[0] if row else 0


# ── Processos de Formulários (Google Forms) ───────────────────────────────────

def get_formularios_cadastrados() -> list:
    """Lista todos os formulários cadastrados."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM formularios_cadastrados ORDER BY ativo DESC, nome'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_formulario_by_form_id(form_id: str) -> dict:
    """Busca formulário cadastrado pelo Google Form ID."""
    if not form_id:
        return None
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM formularios_cadastrados WHERE form_id=? AND ativo=1',
        (form_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def criar_formulario_cadastrado(nome: str, tipo_processo: str,
                                 link: str = '', form_id: str = '',
                                 sheet_id: str = '') -> int:
    """Cria registro de formulário a ser monitorado."""
    conn = get_db()
    cur = conn.execute(
        '''INSERT INTO formularios_cadastrados
           (nome, tipo_processo, link_formulario, form_id, sheet_id)
           VALUES (?, ?, ?, ?, ?)''',
        (nome, tipo_processo, link, form_id, sheet_id)
    )
    fid = cur.lastrowid
    conn.commit()
    conn.close()
    return fid


def toggle_formulario_ativo(form_id: int):
    """Ativa ou desativa um formulário."""
    conn = get_db()
    conn.execute(
        'UPDATE formularios_cadastrados SET ativo = CASE WHEN ativo=1 THEN 0 ELSE 1 END WHERE id=?',
        (form_id,)
    )
    conn.commit()
    conn.close()


def deletar_formulario_cadastrado(form_id: int):
    """Remove registro de formulário (não remove processos já criados)."""
    conn = get_db()
    conn.execute('DELETE FROM formularios_cadastrados WHERE id=?', (form_id,))
    conn.commit()
    conn.close()


def criar_processo_formulario(form_name: str, tipo_processo: str,
                               response_id: str, enviado_por: str,
                               data_envio: str, formulario_id: int = None,
                               link_resposta: str = '') -> int:
    """
    Cria novo processo a partir de uma resposta de formulário.
    Retorna o ID criado, ou None se response_id já existe (deduplicação).
    """
    conn = get_db()
    # Deduplicação: response_id é UNIQUE — inserir ou ignorar
    if response_id:
        existing = conn.execute(
            'SELECT id FROM processos_formularios WHERE response_id=?',
            (response_id,)
        ).fetchone()
        if existing:
            conn.close()
            return None
    cur = conn.execute(
        '''INSERT INTO processos_formularios
           (formulario_id, form_name, tipo_processo, response_id,
            link_resposta, enviado_por, data_envio)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (formulario_id, form_name or 'Formulário', tipo_processo or form_name or '',
         response_id or None, link_resposta or '', enviado_por or '', data_envio or None)
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def inserir_respostas_processo(processo_id: int, respostas: dict):
    """Insere pares pergunta→resposta de um processo."""
    if not respostas:
        return
    conn = get_db()
    for ordem, (pergunta, resposta) in enumerate(respostas.items()):
        conn.execute(
            '''INSERT INTO processos_form_respostas
               (processo_id, pergunta, resposta, ordem)
               VALUES (?, ?, ?, ?)''',
            (processo_id, str(pergunta), str(resposta) if resposta is not None else '', ordem)
        )
    conn.commit()
    conn.close()


def get_processos_formularios(arquivado: int, page: int, per_page: int) -> list:
    """Lista processos paginados com dados do responsável e da última edição das obs."""
    offset = (page - 1) * per_page
    conn = get_db()
    rows = conn.execute(
        '''SELECT p.*,
                  u.nome  AS responsavel_nome,
                  ue.nome AS observacoes_atualizadas_por_nome,
                  fc.form_id AS formulario_form_id,
                  fc.link_formulario AS formulario_link
           FROM processos_formularios p
           LEFT JOIN users u  ON p.responsavel_id = u.id
           LEFT JOIN users ue ON p.observacoes_atualizadas_por = ue.id
           LEFT JOIN formularios_cadastrados fc ON p.formulario_id = fc.id
           WHERE p.arquivado = ?
           ORDER BY COALESCE(p.data_envio, p.criado_em) DESC
           LIMIT ? OFFSET ?''',
        (arquivado, per_page, offset)
    ).fetchall()
    conn.close()
    processos = []
    for r in rows:
        p = dict(r)
        p['respostas'] = get_respostas_processo(p['id'])
        processos.append(p)
    return processos


def count_processos_formularios(arquivado: int) -> int:
    """Conta processos por estado (arquivado ou não)."""
    conn = get_db()
    row = conn.execute(
        'SELECT COUNT(*) FROM processos_formularios WHERE arquivado=?',
        (arquivado,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def get_processo_formulario_by_id(processo_id: int) -> dict:
    """Retorna processo por ID."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM processos_formularios WHERE id=?',
        (processo_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_respostas_processo(processo_id: int) -> list:
    """Retorna todas as respostas de um processo, ordenadas."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM processos_form_respostas WHERE processo_id=? ORDER BY ordem',
        (processo_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_processo_formulario(processo_id: int, campos: dict):
    """Atualiza campos permitidos de um processo (status, responsavel_id, arquivado)."""
    ALLOWED = {'status', 'responsavel_id', 'arquivado'}
    campos_ok = {k: v for k, v in campos.items() if k in ALLOWED}
    if not campos_ok:
        return
    set_clause = ', '.join(f'{k}=?' for k in campos_ok)
    values = list(campos_ok.values()) + [processo_id]
    conn = get_db()
    conn.execute(f'UPDATE processos_formularios SET {set_clause} WHERE id=?', values)
    conn.commit()
    conn.close()


def update_processo_observacoes(processo_id: int, observacoes: str, user_id: int):
    """Salva observações do processo com auditoria de quem editou."""
    conn = get_db()
    conn.execute(
        '''UPDATE processos_formularios
           SET observacoes=?,
               observacoes_atualizadas_em=CURRENT_TIMESTAMP,
               observacoes_atualizadas_por=?
           WHERE id=?''',
        (observacoes, user_id, processo_id)
    )
    conn.commit()
    conn.close()


def get_users_ativos() -> list:
    """Lista usuários ativos para preencher dropdown de responsável."""
    conn = get_db()
    rows = conn.execute(
        'SELECT id, nome FROM users WHERE ativo=1 ORDER BY nome'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Anotações ─────────────────────────────────────────────────────────────────

def get_anotacoes(user_id: int, limit: int = 0) -> list:
    """Retorna anotações do usuário, ordenadas por ordem/id. limit=0 = tudo."""
    conn = get_db()
    sql = '''SELECT id, titulo, conteudo, cor, pos_x, pos_y, largura, altura, ordem,
                    criado_em, atualizado_em
             FROM anotacoes WHERE user_id = ?
             ORDER BY ordem ASC, id ASC'''
    if limit > 0:
        sql += f' LIMIT {int(limit)}'
    rows = conn.execute(sql, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def criar_anotacao(user_id: int, titulo: str = '', conteudo: str = '',
                   cor: str = 'amarelo', pos_x: int = 20, pos_y: int = 20,
                   largura: int = 320, altura: int = 260) -> int:
    """Cria uma nova anotação e retorna o ID."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO anotacoes
           (user_id, titulo, conteudo, cor, pos_x, pos_y, largura, altura)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, titulo, conteudo, cor, pos_x, pos_y, largura, altura)
    )
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()
    return novo_id


def atualizar_anotacao(anotacao_id: int, user_id: int, campos: dict) -> bool:
    """Atualiza campos de uma anotação (pertencente ao user_id). Retorna True se atualizou."""
    permitidos = {'titulo', 'conteudo', 'cor', 'pos_x', 'pos_y', 'largura', 'altura', 'ordem'}
    sets = {k: v for k, v in campos.items() if k in permitidos}
    if not sets:
        return False
    sets_sql = ', '.join(f'{k} = ?' for k in sets)
    vals = list(sets.values()) + [anotacao_id, user_id]
    conn = get_db()
    cur = conn.execute(
        f'UPDATE anotacoes SET {sets_sql}, atualizado_em = CURRENT_TIMESTAMP '
        f'WHERE id = ? AND user_id = ?',
        vals
    )
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def deletar_anotacao(anotacao_id: int, user_id: int) -> bool:
    """Remove uma anotação do usuário. Retorna True se removeu."""
    conn = get_db()
    cur = conn.execute(
        'DELETE FROM anotacoes WHERE id = ? AND user_id = ?',
        (anotacao_id, user_id)
    )
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_ultimos_acessos(user_id: int, limit: int = 3) -> list:
    """Retorna os últimos módulos acessados pelo usuário (distintos, mais recente primeiro)."""
    conn = get_db()
    rows = conn.execute(
        '''SELECT tool, MAX(created_at) as last_at
           FROM activity_log
           WHERE user_id = ?
           GROUP BY tool
           ORDER BY last_at DESC
           LIMIT ?''',
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


