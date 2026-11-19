-- Rode UMA vez no Supabase (menu SQL Editor). Deixa as buscas por aparelho rapidas quando a tabela crescer.
CREATE INDEX IF NOT EXISTS idx_leituras_codigo_id ON public.leituras (codigo_esp32, id);
