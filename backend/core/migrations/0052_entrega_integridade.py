from django.db import migrations


SQL = r'''
CREATE FUNCTION sia_conv_tentativa() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE protocolo_entrega text; entrega_autorizacao bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'tentativa não pode ser removida' USING ERRCODE = '23514';
    ELSIF TG_OP = 'INSERT' THEN
        SELECT protocolo INTO protocolo_entrega FROM core_entregaconviteencontro WHERE id = NEW.entrega_id;
        IF protocolo_entrega IS NULL AND NEW.autorizacao_id IS NULL THEN
            RAISE EXCEPTION 'entrega legada exige autorização' USING ERRCODE = '23514';
        END IF;
        IF NEW.autorizacao_id IS NOT NULL THEN
            SELECT entrega_id INTO entrega_autorizacao FROM core_autorizacaoenvioentregaconvite WHERE id = NEW.autorizacao_id;
            IF entrega_autorizacao IS DISTINCT FROM NEW.entrega_id THEN
                RAISE EXCEPTION 'autorização de outra entrega' USING ERRCODE = '23514';
            END IF;
        END IF;
    ELSE
        IF OLD.desfecho <> 'iniciada' OR NEW.desfecho = 'iniciada' OR NEW.finalizada_em IS NULL OR
           ROW(OLD.id, OLD.entrega_id, OLD.numero, OLD.origem, OLD.autorizacao_id, OLD.chave_idempotencia, OLD.provider, OLD.iniciada_em, OLD.lease_expira_em)
           IS DISTINCT FROM ROW(NEW.id, NEW.entrega_id, NEW.numero, NEW.origem, NEW.autorizacao_id, NEW.chave_idempotencia, NEW.provider, NEW.iniciada_em, NEW.lease_expira_em) THEN
            RAISE EXCEPTION 'transição de tentativa inválida' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER sia_conv_tentativa_tr BEFORE INSERT OR UPDATE OR DELETE ON core_tentativaentregaconvite FOR EACH ROW EXECUTE FUNCTION sia_conv_tentativa();

CREATE FUNCTION sia_conv_autorizacao() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'autorização não pode ser removida' USING ERRCODE = '23514';
    END IF;
    IF OLD.consumida_em IS NOT NULL OR NEW.consumida_em IS NULL OR
       ROW(OLD.id, OLD.entrega_id, OLD.pendencia_id, OLD.evidencia_base_id, OLD.autorizada_por_id, OLD.autorizada_em, OLD.fundamento, OLD.justificativa, OLD.ciencia_duplicidade)
       IS DISTINCT FROM ROW(NEW.id, NEW.entrega_id, NEW.pendencia_id, NEW.evidencia_base_id, NEW.autorizada_por_id, NEW.autorizada_em, NEW.fundamento, NEW.justificativa, NEW.ciencia_duplicidade) THEN
        RAISE EXCEPTION 'transição de autorização inválida' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER sia_conv_autorizacao_tr BEFORE UPDATE OR DELETE ON core_autorizacaoenvioentregaconvite FOR EACH ROW EXECUTE FUNCTION sia_conv_autorizacao();

CREATE FUNCTION sia_conv_imutavel() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'registro imutável' USING ERRCODE = '23514';
END $$;
CREATE TRIGGER sia_conv_evidencia_tr BEFORE UPDATE OR DELETE ON core_evidenciaentregaconvite FOR EACH ROW EXECUTE FUNCTION sia_conv_imutavel();
CREATE TRIGGER sia_conv_auditoria_tr BEFORE UPDATE OR DELETE ON core_eventoauditoriaencontro FOR EACH ROW EXECUTE FUNCTION sia_conv_imutavel();

CREATE FUNCTION sia_conv_pendencia() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'pendência não pode ser removida' USING ERRCODE = '23514';
    END IF;
    IF ROW(OLD.id, OLD.encontro_id, OLD.entrega_id, OLD.tipo, OLD.aberta_em)
       IS DISTINCT FROM ROW(NEW.id, NEW.encontro_id, NEW.entrega_id, NEW.tipo, NEW.aberta_em) THEN
        RAISE EXCEPTION 'identidade da pendência é imutável' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER sia_conv_pendencia_tr BEFORE UPDATE OR DELETE ON core_pendenciaentregaconvite FOR EACH ROW EXECUTE FUNCTION sia_conv_pendencia();

CREATE FUNCTION sia_conv_protocolo() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.protocolo IS DISTINCT FROM NEW.protocolo THEN
        RAISE EXCEPTION 'protocolo é imutável' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER sia_conv_protocolo_tr BEFORE UPDATE ON core_entregaconviteencontro FOR EACH ROW EXECUTE FUNCTION sia_conv_protocolo();
'''

REVERSE = r'''
DROP TRIGGER IF EXISTS sia_conv_tentativa_tr ON core_tentativaentregaconvite;
DROP TRIGGER IF EXISTS sia_conv_autorizacao_tr ON core_autorizacaoenvioentregaconvite;
DROP TRIGGER IF EXISTS sia_conv_evidencia_tr ON core_evidenciaentregaconvite;
DROP TRIGGER IF EXISTS sia_conv_auditoria_tr ON core_eventoauditoriaencontro;
DROP TRIGGER IF EXISTS sia_conv_pendencia_tr ON core_pendenciaentregaconvite;
DROP TRIGGER IF EXISTS sia_conv_protocolo_tr ON core_entregaconviteencontro;
DROP FUNCTION IF EXISTS sia_conv_tentativa();
DROP FUNCTION IF EXISTS sia_conv_autorizacao();
DROP FUNCTION IF EXISTS sia_conv_imutavel();
DROP FUNCTION IF EXISTS sia_conv_pendencia();
DROP FUNCTION IF EXISTS sia_conv_protocolo();
'''


def executar(sql, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(sql)


def criar(apps, schema_editor):
    executar(SQL, schema_editor)


def remover(apps, schema_editor):
    executar(REVERSE, schema_editor)


class Migration(migrations.Migration):
    dependencies = [('core', '0051_entrega_reconciliacao')]
    operations = [migrations.RunPython(criar, remover)]
