-- Flash Sale System Database Schema
-- This script runs automatically when PostgreSQL container starts for the first time

-- ============================================================
-- Table 1: users - 用戶資料表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast username lookup during login
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Index for fast email lookup
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMENT ON TABLE users IS 'Stores user account information';
COMMENT ON COLUMN users.id IS 'Auto-incrementing unique user ID';
COMMENT ON COLUMN users.username IS 'Unique username for login';
COMMENT ON COLUMN users.email IS 'User email address';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password (never store plaintext!)';
COMMENT ON COLUMN users.created_at IS 'Account creation timestamp';


-- ============================================================
-- Table 2: products - 商品資料表
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast stock queries
CREATE INDEX IF NOT EXISTS idx_products_stock ON products(stock);

COMMENT ON TABLE products IS 'Stores product information for flash sales';
COMMENT ON COLUMN products.id IS 'Auto-incrementing unique product ID';
COMMENT ON COLUMN products.name IS 'Product name (e.g., iPhone 15)';
COMMENT ON COLUMN products.description IS 'Product description and details';
COMMENT ON COLUMN products.price IS 'Product price in dollars.cents format';
COMMENT ON COLUMN products.stock IS 'Current stock in database (Redis holds real-time stock during flash sale)';
COMMENT ON COLUMN products.created_at IS 'Product creation timestamp';
COMMENT ON COLUMN products.updated_at IS 'Last update timestamp';


-- ============================================================
-- Table 3: orders - 訂單資料表
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    total_price DECIMAL(10, 2) NOT NULL CHECK (total_price >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints
    CONSTRAINT fk_orders_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_orders_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE RESTRICT
);

-- Index for fast "get user's orders" queries
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);

-- Index for fast "get product's orders" queries
CREATE INDEX IF NOT EXISTS idx_orders_product_id ON orders(product_id);

-- Index for fast status filtering
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Composite index for "get user's orders by status"
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);

COMMENT ON TABLE orders IS 'Stores purchase orders from flash sales';
COMMENT ON COLUMN orders.id IS 'Auto-incrementing unique order ID';
COMMENT ON COLUMN orders.user_id IS 'Foreign key to users.id (who made the purchase)';
COMMENT ON COLUMN orders.product_id IS 'Foreign key to products.id (what was purchased)';
COMMENT ON COLUMN orders.quantity IS 'Number of items purchased (usually 1 for flash sales)';
COMMENT ON COLUMN orders.total_price IS 'Total price (quantity × product price)';
COMMENT ON COLUMN orders.status IS 'Order status: pending, completed, failed, cancelled';
COMMENT ON COLUMN orders.created_at IS 'Order creation timestamp';
COMMENT ON COLUMN orders.updated_at IS 'Last update timestamp';


-- ============================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to products table
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to orders table
CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- Insert Sample Data for Testing
-- ============================================================

-- Sample users (password: "password123" hashed with bcrypt)
-- Note: In production, passwords are hashed by your application
INSERT INTO users (username, email, password_hash) VALUES
    ('alice', 'alice@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS1TuQYem'),
    ('bob', 'bob@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS1TuQYem'),
    ('william', 'william@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS1TuQYem')
ON CONFLICT (username) DO NOTHING;

-- Sample products for flash sale
INSERT INTO products (name, description, price, stock) VALUES
    ('iPhone 15 Pro', 'Latest iPhone with A17 Pro chip, 256GB storage', 999.99, 100),
    ('MacBook Pro 14"', 'M3 chip, 16GB RAM, 512GB SSD', 2499.00, 50),
    ('AirPods Pro 2', 'Active noise cancellation, USB-C charging', 249.00, 200),
    ('Apple Watch Ultra 2', 'Titanium case, GPS + Cellular', 799.00, 80),
    ('iPad Air', '11-inch, M2 chip, 128GB WiFi', 599.00, 150)
ON CONFLICT DO NOTHING;

-- Sample order (Alice bought an iPhone)
INSERT INTO orders (user_id, product_id, quantity, total_price, status) VALUES
    (1, 1, 1, 999.99, 'completed')
ON CONFLICT DO NOTHING;


-- ============================================================
-- Verification Queries (for testing)
-- ============================================================

-- Show all tables
SELECT 'Tables created:' as info;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Show row counts
SELECT 'Row counts:' as info;
SELECT
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM products) as products_count,
    (SELECT COUNT(*) FROM orders) as orders_count;
