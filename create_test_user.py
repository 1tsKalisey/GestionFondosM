"""
Script para crear un usuario de prueba en la base de datos local
Útil para testing sin necesidad de Firebase Auth
"""

import uuid
from datetime import datetime, timezone
from gf_mobile.persistence.db import build_engine, build_session_factory, init_database
from gf_mobile.persistence.models import User, Account, Category

def create_test_user():
    """Crear usuario de prueba con cuenta y categorías básicas"""
    
    # Inicializar BD
    engine = build_engine()
    init_database()
    SessionFactory = build_session_factory(engine)
    session = SessionFactory()
    
    try:
        # Verificar si ya existe un usuario
        existing = session.query(User).first()
        if existing:
            print(f"⚠️  Ya existe un usuario: {existing.email}")
            response = input("¿Deseas crear otro usuario? (s/n): ")
            if response.lower() != 's':
                print("❌ Operación cancelada")
                return
        
        # Datos del usuario de prueba
        email = input("Email del usuario (default: test@example.com): ").strip() or "test@example.com"
        display_name = input("Nombre (default: Usuario Prueba): ").strip() or "Usuario Prueba"
        
        # Crear usuario
        user = User(
            server_uid=f"local_{uuid.uuid4().hex[:16]}",  # UID simulado
            name=display_name,
            created_at=datetime.now(timezone.utc)
        )
        session.add(user)
        session.flush()  # Para obtener el ID
        
        print(f"✅ Usuario creado: {user.name} (ID: {user.id})")
        
        # Crear cuenta por defecto
        account = Account(
            user_id=user.id,
            name="Cuenta Principal",
            type="checking",
            currency="USD",
            opening_balance=1000.00,  # $1000 inicial
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(account)
        
        print(f"✅ Cuenta creada: {account.name} - Balance: ${account.opening_balance}")
        
        # Crear categorías básicas
        categories = [
            ("Alimentación", "Necesidades"),
            ("Transporte", "Necesidades"),
            ("Entretenimiento", "Ocio"),
            ("Salud", "Necesidades"),
            ("Educación", "Necesidades"),
            ("Salario", "Otros"),
            ("Inversiones", "Ahorro"),
            ("Otros Gastos", "Otros"),
        ]
        
        for name, budget_group in categories:
            category = Category(
                name=name,
                budget_group=budget_group,
                created_at=datetime.now(timezone.utc)
            )
            session.add(category)
        
        print(f"✅ {len(categories)} categorías creadas")
        
        # Guardar todo
        session.commit()
        
        print("\n" + "="*60)
        print("🎉 Usuario de prueba creado exitosamente!")
        print("="*60)
        print(f"� Nombre: {user.name}")
        print(f"🆔 Server UID: {user.server_uid}")
        print(f"💰 Cuenta: {account.name} - ${account.opening_balance}")
        print(f"📂 Categorías: {len(categories)}")
        print("\n💡 Ahora puedes ejecutar la app y usar este usuario")
        print("   (No necesitarás autenticarte con Firebase)")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error al crear usuario: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("🔧 Creador de Usuario de Prueba - GestionFondosM")
    print("="*60)
    create_test_user()
