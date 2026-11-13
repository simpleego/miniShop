-- =============================================================================
-- 상품 검색 테스트용 DB 스키마
--
--   DB 이름 : test_vmshop   (운영 DB vmshop 과 분리)
--   구조    : vmshop 과 같은 테이블 + product_querys.md 의 "A안" (추천 필드 + 정렬 인덱스)
--             + 카테고리 (categories 테이블, products.category_id)
--
--   여러 번 실행해도 된다. (테이블을 지우고 다시 만든다 → 기존 테스트 데이터는 사라진다)
--   실행 후 02_test_seed.sql 로 데이터를 채운다.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS test_vmshop
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE test_vmshop;

-- 외래키로 연결된 순서의 반대로 지운다 (자식 → 부모)
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;


-- -----------------------------------------------------------------------------
-- 회원
-- -----------------------------------------------------------------------------
CREATE TABLE users (
  id            INT          NOT NULL AUTO_INCREMENT,
  email         VARCHAR(100) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name          VARCHAR(50)  NOT NULL,
  role          VARCHAR(10)  NOT NULL DEFAULT 'USER',
  status        VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  CONSTRAINT chk_users_role   CHECK (role IN ('USER', 'ADMIN')),
  CONSTRAINT chk_users_status CHECK (status IN ('ACTIVE', 'BLOCKED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- 카테고리 (products 가 참조하므로 products 보다 먼저 만든다)
-- -----------------------------------------------------------------------------
CREATE TABLE categories (
  id   INT         NOT NULL AUTO_INCREMENT,
  name VARCHAR(30) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_categories_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- 상품 (vmshop.products + A안 컬럼 2개 + 카테고리)
--   category_id 는 NULL 허용 : 카테고리를 아직 정하지 않은 상품도 등록할 수 있게 한다
-- -----------------------------------------------------------------------------
CREATE TABLE products (
  id             INT          NOT NULL AUTO_INCREMENT,
  name           VARCHAR(50)  NOT NULL,
  price          INT          NOT NULL,
  stock          INT          NOT NULL DEFAULT 0,
  image_url      VARCHAR(255) DEFAULT NULL,
  description    VARCHAR(255) DEFAULT NULL,
  is_active      TINYINT(1)   NOT NULL DEFAULT 1,
  is_recommended TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '추천 상품 여부',          -- A안
  recommend_rank INT          NOT NULL DEFAULT 0 COMMENT '추천 순서 (클수록 위)',   -- A안
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  category_id    INT          DEFAULT NULL COMMENT '카테고리',
  PRIMARY KEY (id),
  CONSTRAINT chk_products_price CHECK (price >= 0),
  CONSTRAINT chk_products_stock CHECK (stock >= 0),
  CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 정렬용 인덱스 (A안)
CREATE INDEX idx_products_active_created ON products (is_active, created_at);
CREATE INDEX idx_products_active_price   ON products (is_active, price);
CREATE INDEX idx_products_active_reco    ON products (is_active, is_recommended, recommend_rank);


-- -----------------------------------------------------------------------------
-- 주문
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
  id          INT         NOT NULL AUTO_INCREMENT,
  user_id     INT         NOT NULL,
  total_price INT         NOT NULL,
  status      VARCHAR(10) NOT NULL DEFAULT 'PAID',
  created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_orders_user_id (user_id),
  KEY idx_orders_created_at (created_at),
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- 주문 상품
-- -----------------------------------------------------------------------------
CREATE TABLE order_items (
  id         INT NOT NULL AUTO_INCREMENT,
  order_id   INT NOT NULL,
  product_id INT NOT NULL,
  quantity   INT NOT NULL,
  unit_price INT NOT NULL,
  PRIMARY KEY (id),
  KEY fk_items_order (order_id),
  KEY fk_items_product (product_id),
  CONSTRAINT fk_items_order   FOREIGN KEY (order_id)   REFERENCES orders (id),
  CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products (id),
  CONSTRAINT chk_items_quantity CHECK (quantity > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
