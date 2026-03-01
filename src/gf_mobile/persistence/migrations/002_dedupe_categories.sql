-- Normaliza y fusiona categorias duplicadas por (lower(trim(name)), lower(trim(budget_group))).
DROP TABLE IF EXISTS _category_map;
CREATE TEMP TABLE _category_map AS
SELECT
    id AS old_id,
    MIN(id) OVER (
        PARTITION BY lower(trim(name)), lower(trim(budget_group))
    ) AS keep_id
FROM categories;

-- Reasignar referencias directas.
UPDATE transactions
SET category_id = (SELECT keep_id FROM _category_map WHERE old_id = transactions.category_id)
WHERE category_id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id);

UPDATE recurring_transactions
SET category_id = (SELECT keep_id FROM _category_map WHERE old_id = recurring_transactions.category_id)
WHERE category_id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id);

UPDATE subcategories
SET category_id = (SELECT keep_id FROM _category_map WHERE old_id = subcategories.category_id)
WHERE category_id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id);

UPDATE alerts
SET category_id = (SELECT keep_id FROM _category_map WHERE old_id = alerts.category_id)
WHERE category_id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id);

UPDATE savings_goals
SET category_id = (SELECT keep_id FROM _category_map WHERE old_id = savings_goals.category_id)
WHERE category_id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id);

-- Reasignar presupuestos evitando colision de uq_budget_cat_month.
UPDATE budgets
SET category_id = (
    SELECT keep_id FROM _category_map WHERE old_id = budgets.category_id
)
WHERE category_id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id)
  AND NOT EXISTS (
    SELECT 1
    FROM budgets b2
    WHERE b2.category_id = (SELECT keep_id FROM _category_map WHERE old_id = budgets.category_id)
      AND b2.month = budgets.month
  );

DELETE FROM budgets
WHERE category_id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id);

-- Eliminar categorias duplicadas sobrantes.
DELETE FROM categories
WHERE id IN (SELECT old_id FROM _category_map WHERE old_id <> keep_id);

-- Evitar futuros duplicados por diferencias de mayusculas/espacios.
CREATE UNIQUE INDEX IF NOT EXISTS uq_categories_name_group_norm
ON categories(lower(trim(name)), lower(trim(budget_group)));

DROP TABLE IF EXISTS _category_map;
