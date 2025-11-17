import logging
from onbalansprijs.telegram_bot import stuur_telegram_bericht

def beheer_prijsstatus(
    prijs: float,
    laatste_prijs: float | None,
    status: dict,
    timestamp_obj,
    token: str,
    chat_ids: list[str]
):
    """Beheer statusflags en verstuur meldingen op basis van drempels en herstelmeldingen."""
    prijs_rond = round(prijs)
    tijd_str = f"🕒 Tijd: {timestamp_obj.hour}:{timestamp_obj.minute:02}"

    # Alleen verwerken bij prijsverandering
    if prijs_rond != (round(laatste_prijs) if isinstance(laatste_prijs, (int, float)) else laatste_prijs):
        logging.info(f"📊 Onbalansprijs veranderd: {prijs_rond} €/MWh ({tijd_str})")

        # Prioriteit 1: EXTREEM laag (< -500)
        if prijs_rond < -500 and not status.get('extreem_laag', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'🧊 EXTREEM lage onbalansprijs: {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'extreem_laag': True,
                'zeer_laag': True,
                'onder_min_50': True,
                'onder_0': True,
                'onder_50': True,
                'zeer_hoog': False
            })
            return prijs_rond, status

        # Prioriteit 2: ZÉÉR laag (< -150)
        if prijs_rond < -150 and not status.get('zeer_laag', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'❄️ ZÉÉR lage onbalansprijs: {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'zeer_laag': True,
                'onder_min_50': True,
                'onder_0': True,
                'onder_50': True,
                'zeer_hoog': False
            })
            return prijs_rond, status

        # Prioriteit 3: ZÉÉR HOOG (> 400)
        if prijs_rond > 400 and not status.get('zeer_hoog', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'🚨 ZÉÉR HOGE onbalansprijs: {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'zeer_hoog': True,
                'extreem_laag': False,
                'zeer_laag': False,
                'onder_min_50': False,
                'onder_0': False,
                'onder_50': False
            })
            return prijs_rond, status

        # Prioriteit 4: onder -50
        if prijs_rond < -50 and not status.get('onder_min_50', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'🌟 Onbalansprijs onder -50 : {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'onder_min_50': True,
                'onder_0': True,
                'onder_50': True,
                'zeer_hoog': False
            })
            return prijs_rond, status

        # Prioriteit 5: onder 0
        if prijs_rond < 0 and not status.get('onder_0', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'✅ Onbalansprijs onder 0 : {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'onder_0': True,
                'onder_50': True,
                'zeer_hoog': False
            })
            return prijs_rond, status

        # Prioriteit 6: onder 50 (maar boven 0)
        if 0 < prijs_rond < 50 and not status.get('onder_50', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'⚠️ Onbalansprijs onder 50 : {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'onder_50': True,
                'zeer_hoog': False
            })
            return prijs_rond, status

        # Herstelmeldingen (hoogste prioriteit eerst)
        # Herstel: boven 50
        if prijs_rond >= 50 and status.get('onder_50', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'🚨 Onbalansprijs boven 50 : {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'onder_50': False,
                'onder_0': False,
                'onder_min_50': False
            })

        # Herstel: boven 0
        elif prijs_rond >= 0 and status.get('onder_0', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'⚠️ Onbalansprijs boven 0 : {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'onder_0': False,
                'onder_min_50': False
            })

        # Herstel: boven -50
        elif prijs_rond >= -50 and status.get('onder_min_50', False):
            for chat_id in chat_ids:
                stuur_telegram_bericht(token, f'☑️ Onbalansprijs boven -50 : {prijs_rond} €/MWh\n{tijd_str}', chat_id)
            status.update({
                'onder_min_50': False
            })

    return prijs_rond, status
