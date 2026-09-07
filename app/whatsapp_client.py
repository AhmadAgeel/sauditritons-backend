from neonize.aioze.client import NewAClient
from neonize.aioze.events import GroupInfoEv
from neonize.utils import build_jid
from neonize.proto.Neonize_pb2 import JID

from app.database import SessionLocal
from app.config import settings
from app import models


client = NewAClient("neonize.db")

def parse_jid(jid: str) -> JID:
    user, server = jid.split("@", 1)
    return build_jid(user, server)

def jid_to_str(jid: JID) -> str:
    return f"{jid.User}@{jid.Server}"

community_jid = parse_jid(settings.whatsapp_community_jid)
announcements_jid = parse_jid(settings.whatsapp_announcements_jid)

@client.event(GroupInfoEv)
async def on_group_info(client, event: GroupInfoEv):
    if not (
       event.JID == announcements_jid
       and len(event.Join) == 1
       and event.JoinReason == "invite"
    ):
        return
    wa_inv_link = await client.get_group_invite_link(
        community_jid,
        revoke=False,
    )
    await client.get_group_invite_link(
        community_jid,
        revoke=True,
    )

    group_info = await client.get_group_info(announcements_jid)

    lid: JID = event.Join[0]
    participant = next((
        p for p in group_info.Participants
        if p.LID == lid
    ), None)
    wa_user_info = {"lid": jid_to_str(lid)}
    if (
        participant is not None 
        and participant.PhoneNumber.User
    ):
        wa_user_info["phone_number"] = participant.PhoneNumber.User
    
    with SessionLocal() as db:
        wa_user = db.get(models.WhatsAppUser, wa_user_info["lid"])
        if wa_user is None:
            wa_user = models.WhatsAppUser(**wa_user_info)
            db.add(wa_user)
        elif "phone_number" in wa_user_info:
            wa_user.phone_number = wa_user_info["phone_number"]
        db.commit()

        wa_join = models.WhatsAppJoin(
            wa_inv_link=wa_inv_link,
            lid=wa_user_info["lid"],
        )
        db.add(wa_join)
        db.commit()