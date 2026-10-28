"""Regras de decisao da Sprint 3, sem leitura ou gravacao de arquivos."""

from decimal import Decimal, InvalidOperation


def avaliar_regras(
    total: int,
    doentes: int,
    confiancas_novas: list[float],
    *,
    r1_ja_emitida: bool = False,
    r2_ja_emitida: bool = False,
) -> dict:
    """Recebe totais de UM talhao e confiancas apenas dos registros novos.

    Os indicadores usam o historico acumulado depois da importacao.
    Os sinalizadores de repeticao valem para a mesma entrada processada.
    """
    if type(total) is not int or type(doentes) is not int:
        raise ValueError("Total e doentes devem ser numeros inteiros.")
    if total < 0 or not 0 <= doentes <= total:
        raise ValueError("Contagens invalidas.")

    try:
        confiancas = [Decimal(str(v)) for v in confiancas_novas]
    except (InvalidOperation, ValueError) as erro:
        raise ValueError("Confianca invalida.") from erro

    if any(not v.is_finite() or not 0 <= v <= 1 for v in confiancas):
        raise ValueError("Confiancas devem estar entre 0 e 1.")
    if len(confiancas) > total:
        raise ValueError("Ha mais registros novos que registros no historico.")

    media = (
        sum(confiancas, Decimal(0)) / len(confiancas)
        if confiancas else None
    )
    pode_agir = total >= 10 and bool(confiancas)
    alerta = pode_agir and doentes * 100 > total * 30 and not r1_ja_emitida

    alta_proporcao = doentes * 100 > total * 50
    baixa_confianca = media is not None and media < Decimal("0.65")
    relatorio = (
        pode_agir
        and (alta_proporcao or baixa_confianca)
        and not r2_ja_emitida
    )

    motivos = []
    if relatorio:
        if alta_proporcao:
            motivos.append("mais_de_50_porcento_doentes")
        if baixa_confianca:
            motivos.append("baixa_confianca")

    return {
        "alerta": alerta,
        "relatorio": relatorio,
        "motivos": motivos,
        "percentual_doentes": 100 * doentes / total if total else None,
        "confianca_media_novos": float(media) if media is not None else None,
    }