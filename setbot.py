# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Select, Button
import asyncio
from datetime import datetime

# ===========================
# CONFIGURAÇÕES GERAIS
# ===========================
import os
TOKEN = os.getenv("TOKEN")
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

# ===========================
# IDs FIXOS DO SERVIDOR
# ===========================
GUILD_ID = 1433832587713056790
CATEGORIA_APROVACAO_ID = 1435353856375787580  # ✅ Categoria onde serão criados os canais de aprovação
CANAL_FINAL_ID = 1435339952719401092           # Canal de mensagens públicas (aprovado/negado)
CANAL_LOGS_ID = 1435341434256359426           # Canal de logs internos

# Cargos autorizados para aprovar/negar
CARGOS_APROVADORES = [
    1433833526364602441,
    1433844350848208976,
    1434020807272693843
]

# Cargos de solicitação
CARGO_JOVEM = 1433844723025711104
CARGO_MEMBRO = 1433844613516361828


# ===========================
# MODAL DE SOLICITAÇÃO
# ===========================
class SetModal(Modal, title="📋 Solicitação de Set - Restaurante 6"):
    nome_discord = TextInput(label="Nome (Discord):", placeholder="Digite exatamente seu nome no Discord", required=True)
    nome_ingame = TextInput(label="Nome InGame:", placeholder="Ex: Dante", required=True)
    passaporte = TextInput(label="Passaporte:", placeholder="Somente números", required=True)
    telefone = TextInput(label="Telefone:", placeholder="(xx) xxxxx-xxxx", required=True)
    recrutador = TextInput(label="Recrutador:", placeholder="Nome do recrutador", required=True)

    def __init__(self, cargo_id, cargo_nome):
        super().__init__()
        self.cargo_id = cargo_id
        self.cargo_nome = cargo_nome

    async def on_submit(self, interaction: discord.Interaction):
        if not self.passaporte.value.isdigit():
            await interaction.response.send_message("❌ O campo **Passaporte** deve conter apenas números.", ephemeral=True)
            return

        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, id=CATEGORIA_APROVACAO_ID)

        # ✅ Cria canal temporário de aprovação dentro da categoria especificada
        canal_temp = await guild.create_text_channel(
            name=f"aprovação-{self.nome_ingame.value.lower().replace(' ', '-')}",
            category=categoria
        )

        embed = discord.Embed(title="👑 Nova Solicitação de Set", color=0xFFD700)
        embed.add_field(name="📍 Organização", value="Restaurante 6", inline=False)
        embed.add_field(name="🪪 Nome (Discord)", value=self.nome_discord.value, inline=False)
        embed.add_field(name="🎮 Nome InGame", value=self.nome_ingame.value, inline=False)
        embed.add_field(name="📜 Passaporte", value=self.passaporte.value, inline=False)
        embed.add_field(name="📱 Telefone", value=self.telefone.value, inline=False)
        embed.add_field(name="📋 Cargo Solicitado", value=self.cargo_nome, inline=False)
        embed.add_field(name="🧑‍💼 Recrutador", value=self.recrutador.value, inline=False)
        embed.set_footer(text="───────────────\nCapello System ✨", icon_url="https://cdn-icons-png.flaticon.com/512/565/565547.png")

        view = AprovarView(
            self.cargo_id,
            canal_temp,
            embed,
            self.nome_discord.value,
            self.nome_ingame.value,
            self.passaporte.value,
            self.cargo_nome,
            self.recrutador.value,
        )

        await canal_temp.send(
            content=f"<@&{CARGOS_APROVADORES[0]}> Nova solicitação aguardando aprovação:",
            embed=embed,
            view=view
        )
        await interaction.response.send_message("✅ Solicitação enviada com sucesso! Aguarde a aprovação.", ephemeral=True)


# ===========================
# MODAL DE MOTIVO (NEGAR)
# ===========================
class MotivoModal(Modal, title="❌ Motivo da Negação"):
    motivo = TextInput(label="Motivo:", placeholder="Descreva brevemente o motivo da recusa", required=True)

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        await self.parent_view.finalizar_negacao(interaction, self.motivo.value)


# ===========================
# VIEW DE APROVAÇÃO
# ===========================
class AprovarView(View):
    def __init__(self, cargo_id, canal_temp, embed, nome_discord, nome_ingame, passaporte, cargo_nome, recrutador):
        super().__init__(timeout=None)
        self.cargo_id = cargo_id
        self.canal_temp = canal_temp
        self.embed = embed
        self.nome_discord = nome_discord
        self.nome_ingame = nome_ingame
        self.passaporte = passaporte
        self.cargo_nome = cargo_nome
        self.recrutador = recrutador

    # ======== APROVAR ========
    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not any(role.id in CARGOS_APROVADORES for role in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão para aprovar.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        membro = discord.utils.find(lambda m: m.name == self.nome_discord, guild.members)
        cargo = guild.get_role(self.cargo_id)

        if not membro:
            await interaction.followup.send("⚠️ Membro não encontrado.", ephemeral=True)
            return

        await membro.add_roles(cargo, reason="Solicitação aprovada")
        try:
            await membro.edit(nick=f"{self.nome_ingame} | {self.passaporte}")
        except discord.Forbidden:
            pass

        canal_final = guild.get_channel(CANAL_FINAL_ID)
        canal_logs = guild.get_channel(CANAL_LOGS_ID)

        aprovado_embed = discord.Embed(
            title="🎉 Solicitação Aprovada!",
            description=(
                f"**👤 Nome (Discord):** {self.nome_discord}\n"
                f"**🎮 Nome InGame:** {self.nome_ingame}\n"
                f"**📜 Passaporte:** {self.passaporte}\n"
                f"**📋 Cargo:** {self.cargo_nome}\n"
                f"**🧑‍💼 Recrutador:** {self.recrutador}\n\n"
                f"✅ {membro.mention} foi aprovado e recebeu o cargo **{self.cargo_nome}**!"
            ),
            color=0xFFD700
        )
        aprovado_embed.set_footer(text="Capello System ✨ • Aprovação automática")

        if canal_final:
            await canal_final.send(embed=aprovado_embed)

        if canal_logs:
            log_embed = discord.Embed(
                title="📜 Log de Aprovação de Set",
                description=f"✅ **Aprovado** por {interaction.user.mention}",
                color=0x00FF00,
                timestamp=datetime.now()
            )
            log_embed.add_field(name="👤 Nome (Discord)", value=self.nome_discord, inline=False)
            log_embed.add_field(name="🎮 Nome InGame", value=self.nome_ingame, inline=False)
            log_embed.add_field(name="📋 Cargo", value=self.cargo_nome, inline=False)
            log_embed.add_field(name="🧑‍💼 Recrutador", value=self.recrutador, inline=False)
            await canal_logs.send(embed=log_embed)

        await interaction.followup.send("✅ Solicitação aprovada e registrada!", ephemeral=True)
        await asyncio.sleep(3)
        await self.canal_temp.delete()

    # ======== NEGAR ========
    @discord.ui.button(label="❌ Negar", style=discord.ButtonStyle.danger)
    async def negar(self, interaction: discord.Interaction, button: Button):
        if not any(role.id in CARGOS_APROVADORES for role in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão para negar.", ephemeral=True)
            return
        await interaction.response.send_modal(MotivoModal(self))

    async def finalizar_negacao(self, interaction: discord.Interaction, motivo: str):
        guild = interaction.guild
        canal_final = guild.get_channel(CANAL_FINAL_ID)
        canal_logs = guild.get_channel(CANAL_LOGS_ID)

        negado_embed = discord.Embed(
            title="🚫 Solicitação Negada",
            description=(
                f"**👤 Nome (Discord):** {self.nome_discord}\n"
                f"**🎮 Nome InGame:** {self.nome_ingame}\n"
                f"**📜 Passaporte:** {self.passaporte}\n"
                f"**📋 Cargo:** {self.cargo_nome}\n"
                f"**🧑‍💼 Recrutador:** {self.recrutador}\n\n"
                f"❌ **Motivo:** {motivo}"
            ),
            color=0xFF0000
        )
        negado_embed.set_footer(text="Capello System ✨ • Avaliação encerrada")

        if canal_final:
            await canal_final.send(embed=negado_embed)

        if canal_logs:
            log_embed = discord.Embed(
                title="📜 Log de Negação de Set",
                description=f"❌ **Negado** por {interaction.user.mention}",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            log_embed.add_field(name="👤 Nome (Discord)", value=self.nome_discord, inline=False)
            log_embed.add_field(name="🎮 Nome InGame", value=self.nome_ingame, inline=False)
            log_embed.add_field(name="📋 Cargo", value=self.cargo_nome, inline=False)
            log_embed.add_field(name="🧑‍💼 Recrutador", value=self.recrutador, inline=False)
            log_embed.add_field(name="❌ Motivo", value=motivo, inline=False)
            await canal_logs.send(embed=log_embed)

        # ✅ Correção: usa response.send_message (não followup)
        await interaction.response.send_message("🚫 Solicitação negada e registrada.", ephemeral=True)

        await asyncio.sleep(3)
        await self.canal_temp.delete()


# ===========================
# PAINEL PRINCIPAL
# ===========================
class PainelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CargoSelect())


class CargoSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="👨‍🍳 Jovem Aprendiz", value="jovem"),
            discord.SelectOption(label="👔 Membro", value="membro"),
        ]
        super().__init__(placeholder="Selecione o cargo que deseja solicitar", options=options)

    async def callback(self, interaction: discord.Interaction):
        cargo_id = CARGO_JOVEM if self.values[0] == "jovem" else CARGO_MEMBRO
        cargo_nome = "Jovem Aprendiz" if self.values[0] == "jovem" else "Membro"
        await interaction.response.send_modal(SetModal(cargo_id, cargo_nome))


# ===========================
# COMANDO PARA CRIAR PAINEL
# ===========================
@bot.command()
async def painel2(ctx):
    embed = discord.Embed(
        title="🍽️ Painel de Solicitação de Set - Restaurante 6",
        description=(
            "Bem-vindo ao sistema de solicitação de set da organização **Restaurante 6**!\n\n"
            "🔹 Preencha as informações com atenção:\n"
            "• **Nome (Discord):** exatamente como aparece no seu perfil\n"
            "• **Nome InGame:** o nome usado dentro do jogo\n"
            "• **Passaporte:** somente números\n"
            "• **Telefone** e **Recrutador** são obrigatórios\n\n"
            "✨ Sistema automatizado by **Capello System**"
        ),
        color=0xFFD700
    )
    embed.set_footer(text="Capello System • Luxo, Tradição e Organização")
    await ctx.send(embed=embed, view=PainelView())


# ===========================
# INICIAR BOT
# ===========================
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

bot.run(TOKEN)
