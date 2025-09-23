#!/usr/bin/env python3
"""
테스트 계정 설정 스크립트
관리자 및 일반 사용자 계정을 미리 생성합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import bcrypt
import sqlite3
from datetime import datetime

def create_test_users():
    """테스트 사용자들을 데이터베이스에 생성"""

    # 데이터베이스 연결
    db_path = "database/crypto_trader.db"

    # 디렉토리가 없으면 생성
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 사용자 테이블 생성 (존재하지 않는 경우)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                account_locked_until TIMESTAMP
            )
        ''')

        # 세션 테이블 생성 (존재하지 않는 경우)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 테스트 사용자 계정 정보
        test_users = [
            {
                'username': 'admin',
                'email': 'admin@cryptotrader.local',
                'password': 'admin123',
                'role': 'admin'
            },
            {
                'username': 'trader1',
                'email': 'trader1@cryptotrader.local',
                'password': 'trader123',
                'role': 'user'
            }
        ]

        for user_data in test_users:
            # 기존 사용자 확인
            cursor.execute('SELECT id FROM users WHERE username = ?', (user_data['username'],))
            existing_user = cursor.fetchone()

            if existing_user:
                print(f"사용자 '{user_data['username']}'이(가) 이미 존재합니다. 업데이트합니다.")

                # 패스워드 해싱
                password_hash = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # 기존 사용자 업데이트
                cursor.execute('''
                    UPDATE users
                    SET password_hash = ?, email = ?, role = ?
                    WHERE username = ?
                ''', (password_hash, user_data['email'], user_data['role'], user_data['username']))

            else:
                print(f"새 사용자 '{user_data['username']}'을(를) 생성합니다.")

                # 패스워드 해싱
                password_hash = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # 새 사용자 생성
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role, is_active, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (
                    user_data['username'],
                    user_data['email'],
                    password_hash,
                    user_data['role'],
                    datetime.now()
                ))

        # 변경사항 저장
        conn.commit()

        print("\n[성공] 테스트 계정이 설정되었습니다!")
        print("\n테스트 계정 정보:")
        print("1. 관리자 계정:")
        print("   - 사용자명: admin")
        print("   - 패스워드: admin123")
        print("   - 권한: 관리자")
        print("\n2. 일반 사용자 계정:")
        print("   - 사용자명: trader1")
        print("   - 패스워드: trader123")
        print("   - 권한: 일반 사용자")

        # 생성된 사용자 확인
        cursor.execute('SELECT username, email, role, created_at FROM users')
        users = cursor.fetchall()

        print(f"\n데이터베이스에 총 {len(users)}명의 사용자가 등록되어 있습니다:")
        for user in users:
            print(f"- {user[0]} ({user[1]}) - {user[2]} - 생성일: {user[3]}")

    except Exception as e:
        print(f"[오류] 테스트 계정 설정 실패: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

def verify_login(username, password):
    """로그인 검증 테스트"""
    db_path = "database/crypto_trader.db"

    if not os.path.exists(db_path):
        print("데이터베이스 파일이 존재하지 않습니다.")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 사용자 조회
        cursor.execute('SELECT password_hash FROM users WHERE username = ? AND is_active = 1', (username,))
        result = cursor.fetchone()

        if not result:
            print(f"사용자 '{username}'을(를) 찾을 수 없습니다.")
            return False

        stored_hash = result[0]

        # 패스워드 검증
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            print(f"[성공] '{username}' 로그인 성공!")
            return True
        else:
            print(f"[실패] '{username}' 패스워드가 일치하지 않습니다.")
            return False

    except Exception as e:
        print(f"[오류] 로그인 검증 실패: {e}")
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    print("=== Crypto Trader Pro 테스트 계정 설정 ===")

    # 테스트 사용자 생성
    create_test_users()

    print("\n=== 로그인 테스트 ===")

    # 로그인 테스트
    verify_login("admin", "admin123")
    verify_login("trader1", "trader123")
    verify_login("invalid_user", "wrong_password")  # 실패 테스트

    print("\n설정 완료! 이제 Streamlit 앱에서 위 계정들로 로그인할 수 있습니다.")