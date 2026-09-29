from pydantic import BaseModel, Field


class CultureChoice(BaseModel):
    culture_id: str
    dialect: str
    region: str
    setting: str = "rural"
    script: str = "roman"


class SceneRecord(BaseModel):
    scene_id: str
    scene_number: int
    int_ext: str
    location: str
    location_id: str
    sub_location: str = ""
    time: str = ""
    day_or_date: str = ""
    weather: str = ""
    mood: str = ""
    summary: str = ""
    dramatic_purpose: str = ""
    characters: list[str] = Field(default_factory=list)
    costume_ids: list[str] = Field(default_factory=list)
    props_in: list[str] = Field(default_factory=list)
    props_out: list[str] = Field(default_factory=list)
    props_present: list[str] = Field(default_factory=list)
    emotional_change: str = ""
    continuity_warnings: list[str] = Field(default_factory=list)
    source_heading: str = ""
    action_lines: list[str] = Field(default_factory=list)
    dialogue: list[dict] = Field(default_factory=list)


class CharacterRecord(BaseModel):
    character_id: str
    source_name: str
    adapted_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    age: str = ""
    role: str = ""
    relationships: list[str] = Field(default_factory=list)
    personality: str = ""
    dialect: str = ""
    emotional_state: str = ""
    entrance_scene: str = ""
    exit_scene: str = ""
    physical_description: str = ""
    grooming: str = ""
    approved: bool = False


class ProductionElement(BaseModel):
    element_id: str
    kind: str
    source_name: str
    adapted_name: str = ""
    description: str = ""
    first_scene: str = ""
    scenes: list[str] = Field(default_factory=list)
    approved: bool = False


class CostumeRecord(BaseModel):
    costume_id: str
    character_id: str
    label: str
    garments: str = ""
    fabrics: str = ""
    colours: list[str] = Field(default_factory=list)
    footwear: str = ""
    jewellery: str = ""
    headwear: str = ""
    grooming: str = ""
    scenes: list[str] = Field(default_factory=list)
    change_reason: str = "No story reason to change; reused for continuity."
    approved: bool = False


class ContinuityState(BaseModel):
    scene_id: str
    wearing: dict[str, str] = Field(default_factory=dict)
    carrying: dict[str, list[str]] = Field(default_factory=dict)
    knowledge: dict[str, list[str]] = Field(default_factory=dict)
    injuries: dict[str, list[str]] = Field(default_factory=dict)
    relationships: dict[str, str] = Field(default_factory=dict)
    emotion: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class AdaptationDecision(BaseModel):
    decision_id: str
    topic: str
    source: str
    adapted: str
    reason: str
    uncertainty: str = ""
    needs_review: bool = False


class AdaptationPlan(BaseModel):
    culture: CultureChoice
    summary: str
    decisions: list[AdaptationDecision] = Field(default_factory=list)
    uncertain_choices: list[str] = Field(default_factory=list)
    approved: bool = False


class VisualAsset(BaseModel):
    asset_id: str
    kind: str
    canonical_id: str
    title: str
    path: str
    prompt: str
    model: str = "svg-renderer-v1"
    seed: str = ""
    status: str = "pending"
    error: str = ""


class ProjectState(BaseModel):
    project_id: str
    source_filename: str = "pasted.txt"
    source_text: str
    culture: CultureChoice
    extraction_problems: list[str] = Field(default_factory=list)
    scenes: list[SceneRecord] = Field(default_factory=list)
    characters: list[CharacterRecord] = Field(default_factory=list)
    locations: list[ProductionElement] = Field(default_factory=list)
    props: list[ProductionElement] = Field(default_factory=list)
    costumes: list[CostumeRecord] = Field(default_factory=list)
    continuity: list[ContinuityState] = Field(default_factory=list)
    adaptation_plan: AdaptationPlan | None = None
    adapted_screenplay: str = ""
    adapted_screenplay_gurmukhi: str = ""
    change_log: list[dict] = Field(default_factory=list)
    visuals: list[VisualAsset] = Field(default_factory=list)
    extraction_approved: bool = False
    costumes_approved: bool = False
    model_calls: int = 0
    tool_calls: int = 0
    human_notes: list[str] = Field(default_factory=list)
