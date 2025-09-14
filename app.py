from flask import Flask, render_template, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
import os


app = Flask(__name__)
app.secret_key = 'admin123'  # Necesario para usar session
ADMIN_PASSWORD = 'admin123'  # Cambia por la que quieras

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'success': False, 'error': 'Contraseña requerida'})
    
    if data['password'] == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Contraseña incorrecta'})

@app.route('/logout', methods=['POST'])
def logout():
    session['is_admin'] = False
    return jsonify({'success': True})

# Configuración de la base de datos
# Para desarrollo local usa SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///rifa.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de la base de datos
class Numero(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendido = db.Column(db.Boolean, default=False, nullable=False)
    comprador = db.Column(db.String(100), nullable=True)  # Nuevo campo para el nombre

    def __repr__(self):
        estado = "Vendido" if self.vendido else "Disponible"
        return f'<Numero {self.id}: {estado}, Comprador: {self.comprador}>'


# Crear las tablas y datos iniciales
def init_db():
    """Inicializa la base de datos con los 100 números"""
    db.create_all()
    
    # Verificar si ya existen números
    if Numero.query.count() == 0:
        # Crear números del 0 al 99
        for i in range(100):
            numero = Numero(id=i, vendido=False)
            db.session.add(numero)
        
        try:
            db.session.commit()
            print("Base de datos inicializada con 100 números")
        except Exception as e:
            db.session.rollback()
            print(f"Error inicializando la base de datos: {e}")

# Rutas principales
@app.route('/')
def index():
    """Página principal con la grilla de números"""
    return render_template('index.html')

@app.route('/estado')
def obtener_estado():
    """API que devuelve el estado actual de todos los números"""
    try:
        numeros = Numero.query.all()
        estado = {}
        for numero in numeros:
            estado[numero.id] = numero.vendido
        return jsonify({
            'success': True,
            'numeros': estado,
            'total_vendidos': sum(1 for n in numeros if n.vendido),
            'disponibles': sum(1 for n in numeros if not n.vendido)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/vender/<int:num>', methods=['POST'])
def vender(num):
    """Marca un número como vendido"""
    try:
        # Validar que el número esté en el rango correcto
        if num < 0 or num >= 100:
            return jsonify({
                'success': False, 
                'error': 'Número fuera de rango'
            })
        
        # Buscar el número en la base de datos
        numero = Numero.query.get(num)
        
        if not numero:
            return jsonify({
                'success': False, 
                'error': 'Número no encontrado'
            })
        
        # Verificar si ya está vendido
        if numero.vendido:
            return jsonify({
                'success': False, 
                'error': 'Este número ya está vendido'
            })
        
        # Marcar como vendido
        numero.vendido = True
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Número {num:02d} vendido exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': f'Error al procesar la venta: {str(e)}'
        })

@app.route('/admin/reset', methods=['POST'])
def reset_rifa():
    """Ruta de administrador para reiniciar la rifa"""
    try:
        # Verificar que sea administrador
        if not session.get('is_admin', False):
            return jsonify({'success': False, 'error': 'Solo los administradores pueden reiniciar la rifa'})

            
        # Marcar todos los números como no vendidos
        Numero.query.update({Numero.vendido: False})
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Rifa reiniciada exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': f'Error al reiniciar: {str(e)}'
        })

@app.route('/admin/estadisticas')
def estadisticas():
    """Ruta para ver estadísticas de la rifa"""
    try:
        total_numeros = Numero.query.count()
        vendidos = Numero.query.filter_by(vendido=True).count()
        disponibles = total_numeros - vendidos
        porcentaje_vendido = (vendidos / total_numeros * 100) if total_numeros > 0 else 0
        
        return jsonify({
            'success': True,
            'total_numeros': total_numeros,
            'vendidos': vendidos,
            'disponibles': disponibles,
            'porcentaje_vendido': round(porcentaje_vendido, 2)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Manejo de errores
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Página no encontrada'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

# Inicializar la aplicación
if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    # Para desarrollo local
    app.run(debug=True, host='0.0.0.0', port=5000)