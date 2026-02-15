"""Knowledge Graph Schema Definitions for MegaAgent Pro.

Provides schema definitions for knowledge graph construction and querying:
- Entity types and relationships for EB-1A domain
- Schema validation utilities
- Graph construction helpers
- Query templates for common patterns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from typing import Any


class EntityType(Enum):
    """Entity types in the knowledge graph."""

    # Core entities
    PERSON = "person"
    ORGANIZATION = "organization"
    PUBLICATION = "publication"
    AWARD = "award"
    PATENT = "patent"
    PROJECT = "project"
    EVENT = "event"

    # EB-1A specific
    CRITERION = "criterion"
    EVIDENCE = "evidence"
    RECOMMENDATION = "recommendation"
    CASE = "case"
    PETITION = "petition"

    # Domain entities
    FIELD = "field"
    SKILL = "skill"
    ACHIEVEMENT = "achievement"
    POSITION = "position"
    MEMBERSHIP = "membership"
    MEDIA_COVERAGE = "media_coverage"
    CITATION = "citation"
    REVIEW = "review"
    CONTRIBUTION = "contribution"

    # Meta entities
    DOCUMENT = "document"
    CHUNK = "chunk"
    CONCEPT = "concept"
    TOPIC = "topic"


class RelationType(Enum):
    """Relationship types in the knowledge graph."""

    # Person relationships
    AUTHORED = "authored"
    RECEIVED = "received"
    INVENTED = "invented"
    WORKS_AT = "works_at"
    MEMBER_OF = "member_of"
    JUDGED = "judged"
    CONTRIBUTED_TO = "contributed_to"
    SUPERVISED = "supervised"
    COLLABORATED_WITH = "collaborated_with"

    # Publication relationships
    CITED_BY = "cited_by"
    PUBLISHED_IN = "published_in"
    RELATED_TO = "related_to"

    # Evidence relationships
    SUPPORTS = "supports"
    DOCUMENTS = "documents"
    DEMONSTRATES = "demonstrates"
    PROVES = "proves"

    # EB-1A relationships
    MEETS_CRITERION = "meets_criterion"
    EVIDENCE_FOR = "evidence_for"
    RECOMMENDS = "recommends"
    PART_OF_CASE = "part_of_case"

    # Hierarchical
    PART_OF = "part_of"
    HAS_PART = "has_part"
    CONTAINS = "contains"
    BELONGS_TO = "belongs_to"

    # Semantic
    SIMILAR_TO = "similar_to"
    INSTANCE_OF = "instance_of"
    SUBTYPE_OF = "subtype_of"
    ASSOCIATED_WITH = "associated_with"


@dataclass
class PropertySchema:
    """Schema for entity/relationship properties."""

    name: str
    data_type: str  # string, integer, float, boolean, datetime, json
    required: bool = False
    indexed: bool = False
    unique: bool = False
    default: Any = None
    validators: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class EntitySchema:
    """Schema definition for an entity type."""

    entity_type: EntityType
    properties: dict[str, PropertySchema]
    required_properties: list[str] = field(default_factory=list)
    indexed_properties: list[str] = field(default_factory=list)
    unique_constraints: list[str] = field(default_factory=list)
    description: str = ""

    def validate(self, entity_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate entity data against schema."""
        errors = []

        # Check required properties
        for prop in self.required_properties:
            if prop not in entity_data or entity_data[prop] is None:
                errors.append(f"Missing required property: {prop}")

        # Validate property types
        for prop_name, value in entity_data.items():
            if prop_name in self.properties:
                schema = self.properties[prop_name]
                type_valid, type_error = self._validate_type(value, schema.data_type)
                if not type_valid:
                    errors.append(f"Property {prop_name}: {type_error}")

        return len(errors) == 0, errors

    def _validate_type(self, value: Any, expected_type: str) -> tuple[bool, str]:
        """Validate value type."""
        if value is None:
            return True, ""

        type_mapping = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "boolean": bool,
            "datetime": (str, datetime),
            "json": (dict, list),
        }

        expected = type_mapping.get(expected_type)
        if expected and not isinstance(value, expected):
            return False, f"Expected {expected_type}, got {type(value).__name__}"
        return True, ""


@dataclass
class RelationshipSchema:
    """Schema definition for a relationship type."""

    relation_type: RelationType
    source_types: list[EntityType]
    target_types: list[EntityType]
    properties: dict[str, PropertySchema] = field(default_factory=dict)
    bidirectional: bool = False
    max_cardinality: int | None = None  # None means unlimited
    description: str = ""

    def validate_connection(
        self,
        source_type: EntityType,
        target_type: EntityType,
    ) -> tuple[bool, str]:
        """Validate that source and target types are allowed."""
        if source_type not in self.source_types:
            return (
                False,
                f"Invalid source type {source_type.value} for relation {self.relation_type.value}",
            )
        if target_type not in self.target_types:
            return (
                False,
                f"Invalid target type {target_type.value} for relation {self.relation_type.value}",
            )
        return True, ""


@dataclass
class Entity:
    """Entity instance in the knowledge graph."""

    id: str
    entity_type: EntityType
    properties: dict[str, Any]
    embedding: list[float] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.entity_type.value,
            "properties": self.properties,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            entity_type=EntityType(data["type"]),
            properties=data["properties"],
            embedding=data.get("embedding"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if isinstance(data.get("created_at"), str)
                else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if isinstance(data.get("updated_at"), str)
                else datetime.now()
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Relationship:
    """Relationship instance in the knowledge graph."""

    id: str
    relation_type: RelationType
    source_id: str
    target_id: str
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.relation_type.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "properties": self.properties,
            "weight": self.weight,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            relation_type=RelationType(data["type"]),
            source_id=data["source_id"],
            target_id=data["target_id"],
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if isinstance(data.get("created_at"), str)
                else datetime.now()
            ),
            metadata=data.get("metadata", {}),
        )


class KnowledgeGraphSchema:
    """Complete schema for the knowledge graph."""

    def __init__(self):
        self.entity_schemas: dict[EntityType, EntitySchema] = {}
        self.relationship_schemas: dict[RelationType, RelationshipSchema] = {}
        self._initialize_default_schemas()

    def _initialize_default_schemas(self) -> None:
        """Initialize default EB-1A domain schemas."""
        # Person entity schema
        self.entity_schemas[EntityType.PERSON] = EntitySchema(
            entity_type=EntityType.PERSON,
            properties={
                "name": PropertySchema("name", "string", required=True, indexed=True),
                "full_name": PropertySchema("full_name", "string"),
                "email": PropertySchema("email", "string", unique=True),
                "nationality": PropertySchema("nationality", "string"),
                "field_of_expertise": PropertySchema("field_of_expertise", "string", indexed=True),
                "current_position": PropertySchema("current_position", "string"),
                "bio": PropertySchema("bio", "string"),
                "h_index": PropertySchema("h_index", "integer"),
                "citation_count": PropertySchema("citation_count", "integer"),
            },
            required_properties=["name"],
            indexed_properties=["name", "field_of_expertise"],
            description="Person entity - researchers, applicants, reviewers",
        )

        # Publication entity schema
        self.entity_schemas[EntityType.PUBLICATION] = EntitySchema(
            entity_type=EntityType.PUBLICATION,
            properties={
                "title": PropertySchema("title", "string", required=True, indexed=True),
                "abstract": PropertySchema("abstract", "string"),
                "doi": PropertySchema("doi", "string", unique=True),
                "year": PropertySchema("year", "integer", indexed=True),
                "venue": PropertySchema("venue", "string"),
                "venue_type": PropertySchema("venue_type", "string"),  # journal, conference, book
                "citation_count": PropertySchema("citation_count", "integer"),
                "impact_factor": PropertySchema("impact_factor", "float"),
                "quartile": PropertySchema("quartile", "string"),  # Q1, Q2, Q3, Q4
            },
            required_properties=["title"],
            indexed_properties=["title", "year", "doi"],
            description="Publication entity - papers, articles, books",
        )

        # Award entity schema
        self.entity_schemas[EntityType.AWARD] = EntitySchema(
            entity_type=EntityType.AWARD,
            properties={
                "name": PropertySchema("name", "string", required=True, indexed=True),
                "organization": PropertySchema("organization", "string"),
                "year": PropertySchema("year", "integer"),
                "level": PropertySchema("level", "string"),  # national, international, local
                "field": PropertySchema("field", "string"),
                "description": PropertySchema("description", "string"),
                "criteria": PropertySchema("criteria", "string"),
                "selectivity": PropertySchema(
                    "selectivity", "string"
                ),  # highly selective, selective, etc.
            },
            required_properties=["name"],
            indexed_properties=["name", "year", "level"],
            description="Award entity - prizes, honors, recognitions",
        )

        # Criterion entity schema (EB-1A specific)
        self.entity_schemas[EntityType.CRITERION] = EntitySchema(
            entity_type=EntityType.CRITERION,
            properties={
                "number": PropertySchema("number", "integer", required=True, unique=True),
                "name": PropertySchema("name", "string", required=True),
                "description": PropertySchema("description", "string"),
                "evidence_types": PropertySchema("evidence_types", "json"),
                "requirements": PropertySchema("requirements", "json"),
            },
            required_properties=["number", "name"],
            indexed_properties=["number", "name"],
            description="EB-1A criterion - one of 10 qualifying criteria",
        )

        # Evidence entity schema
        self.entity_schemas[EntityType.EVIDENCE] = EntitySchema(
            entity_type=EntityType.EVIDENCE,
            properties={
                "title": PropertySchema("title", "string", required=True),
                "type": PropertySchema(
                    "type", "string", indexed=True
                ),  # document, letter, award, etc.
                "description": PropertySchema("description", "string"),
                "strength": PropertySchema("strength", "string"),  # strong, moderate, weak
                "source": PropertySchema("source", "string"),
                "date": PropertySchema("date", "string"),
            },
            required_properties=["title", "type"],
            indexed_properties=["type", "strength"],
            description="Evidence entity - supporting documents and materials",
        )

        # Organization entity schema
        self.entity_schemas[EntityType.ORGANIZATION] = EntitySchema(
            entity_type=EntityType.ORGANIZATION,
            properties={
                "name": PropertySchema("name", "string", required=True, indexed=True),
                "type": PropertySchema("type", "string"),  # university, company, government, etc.
                "country": PropertySchema("country", "string"),
                "ranking": PropertySchema("ranking", "integer"),
                "prestige_level": PropertySchema("prestige_level", "string"),
            },
            required_properties=["name"],
            indexed_properties=["name", "type", "country"],
            description="Organization entity - institutions, companies",
        )

        # Initialize relationship schemas
        self._initialize_relationship_schemas()

    def _initialize_relationship_schemas(self) -> None:
        """Initialize default relationship schemas."""
        # AUTHORED relationship
        self.relationship_schemas[RelationType.AUTHORED] = RelationshipSchema(
            relation_type=RelationType.AUTHORED,
            source_types=[EntityType.PERSON],
            target_types=[EntityType.PUBLICATION, EntityType.PATENT],
            properties={
                "author_position": PropertySchema("author_position", "integer"),
                "is_corresponding": PropertySchema("is_corresponding", "boolean"),
            },
            description="Person authored a publication or patent",
        )

        # RECEIVED relationship
        self.relationship_schemas[RelationType.RECEIVED] = RelationshipSchema(
            relation_type=RelationType.RECEIVED,
            source_types=[EntityType.PERSON],
            target_types=[EntityType.AWARD],
            properties={
                "year": PropertySchema("year", "integer"),
            },
            description="Person received an award",
        )

        # MEETS_CRITERION relationship
        self.relationship_schemas[RelationType.MEETS_CRITERION] = RelationshipSchema(
            relation_type=RelationType.MEETS_CRITERION,
            source_types=[EntityType.PERSON, EntityType.CASE],
            target_types=[EntityType.CRITERION],
            properties={
                "strength": PropertySchema("strength", "string"),
                "confidence": PropertySchema("confidence", "float"),
            },
            description="Person/Case meets an EB-1A criterion",
        )

        # EVIDENCE_FOR relationship
        self.relationship_schemas[RelationType.EVIDENCE_FOR] = RelationshipSchema(
            relation_type=RelationType.EVIDENCE_FOR,
            source_types=[
                EntityType.EVIDENCE,
                EntityType.PUBLICATION,
                EntityType.AWARD,
                EntityType.PATENT,
            ],
            target_types=[EntityType.CRITERION],
            properties={
                "relevance": PropertySchema("relevance", "float"),
                "description": PropertySchema("description", "string"),
            },
            description="Evidence supports a criterion",
        )

        # CITED_BY relationship
        self.relationship_schemas[RelationType.CITED_BY] = RelationshipSchema(
            relation_type=RelationType.CITED_BY,
            source_types=[EntityType.PUBLICATION],
            target_types=[EntityType.PUBLICATION],
            properties={
                "citation_context": PropertySchema("citation_context", "string"),
            },
            bidirectional=False,
            description="Publication cited by another publication",
        )

        # WORKS_AT relationship
        self.relationship_schemas[RelationType.WORKS_AT] = RelationshipSchema(
            relation_type=RelationType.WORKS_AT,
            source_types=[EntityType.PERSON],
            target_types=[EntityType.ORGANIZATION],
            properties={
                "position": PropertySchema("position", "string"),
                "start_date": PropertySchema("start_date", "string"),
                "end_date": PropertySchema("end_date", "string"),
                "is_current": PropertySchema("is_current", "boolean"),
            },
            description="Person works at an organization",
        )

        # RECOMMENDS relationship
        self.relationship_schemas[RelationType.RECOMMENDS] = RelationshipSchema(
            relation_type=RelationType.RECOMMENDS,
            source_types=[EntityType.PERSON],
            target_types=[EntityType.PERSON, EntityType.CASE],
            properties={
                "relationship_type": PropertySchema(
                    "relationship_type", "string"
                ),  # independent, collaborator, etc.
                "letter_date": PropertySchema("letter_date", "string"),
            },
            description="Person recommends another person/case",
        )

    def get_entity_schema(self, entity_type: EntityType) -> EntitySchema | None:
        """Get schema for entity type."""
        return self.entity_schemas.get(entity_type)

    def get_relationship_schema(self, relation_type: RelationType) -> RelationshipSchema | None:
        """Get schema for relationship type."""
        return self.relationship_schemas.get(relation_type)

    def validate_entity(self, entity: Entity) -> tuple[bool, list[str]]:
        """Validate entity against schema."""
        schema = self.get_entity_schema(entity.entity_type)
        if not schema:
            return False, [f"Unknown entity type: {entity.entity_type}"]
        return schema.validate(entity.properties)

    def validate_relationship(
        self,
        relationship: Relationship,
        source_entity: Entity,
        target_entity: Entity,
    ) -> tuple[bool, list[str]]:
        """Validate relationship against schema."""
        schema = self.get_relationship_schema(relationship.relation_type)
        if not schema:
            return False, [f"Unknown relationship type: {relationship.relation_type}"]

        valid, error = schema.validate_connection(
            source_entity.entity_type,
            target_entity.entity_type,
        )
        if not valid:
            return False, [error]

        return True, []

    def to_dict(self) -> dict[str, Any]:
        """Export schema to dictionary."""
        return {
            "entity_schemas": {
                et.value: {
                    "properties": {
                        name: {
                            "name": prop.name,
                            "data_type": prop.data_type,
                            "required": prop.required,
                            "indexed": prop.indexed,
                            "unique": prop.unique,
                        }
                        for name, prop in schema.properties.items()
                    },
                    "required_properties": schema.required_properties,
                    "indexed_properties": schema.indexed_properties,
                    "description": schema.description,
                }
                for et, schema in self.entity_schemas.items()
            },
            "relationship_schemas": {
                rt.value: {
                    "source_types": [st.value for st in schema.source_types],
                    "target_types": [tt.value for tt in schema.target_types],
                    "bidirectional": schema.bidirectional,
                    "description": schema.description,
                }
                for rt, schema in self.relationship_schemas.items()
            },
        }

    def to_json(self) -> str:
        """Export schema to JSON."""
        return json.dumps(self.to_dict(), indent=2)


# EB-1A Criteria Constants
EB1A_CRITERIA = {
    1: {
        "name": "Awards",
        "description": "Documentation of receipt of lesser nationally or internationally recognized prizes or awards for excellence in the field",
        "evidence_types": ["award_certificate", "news_coverage", "organization_verification"],
    },
    2: {
        "name": "Membership",
        "description": "Documentation of membership in associations that require outstanding achievements",
        "evidence_types": ["membership_certificate", "selection_criteria", "member_list"],
    },
    3: {
        "name": "Published Material",
        "description": "Published material about the alien in professional or major trade publications",
        "evidence_types": ["articles", "interviews", "profiles"],
    },
    4: {
        "name": "Judging",
        "description": "Evidence of participation as a judge of the work of others",
        "evidence_types": ["review_invitations", "editorial_board", "panel_participation"],
    },
    5: {
        "name": "Original Contributions",
        "description": "Evidence of original scientific, scholarly, artistic contributions of major significance",
        "evidence_types": ["patents", "publications", "adoption_evidence", "expert_letters"],
    },
    6: {
        "name": "Scholarly Articles",
        "description": "Evidence of authorship of scholarly articles in professional journals",
        "evidence_types": ["publications", "citation_metrics", "journal_rankings"],
    },
    7: {
        "name": "Artistic Exhibitions",
        "description": "Evidence of display of work at artistic exhibitions or showcases",
        "evidence_types": ["exhibition_catalogs", "venue_information", "media_coverage"],
    },
    8: {
        "name": "Leading Role",
        "description": "Evidence of performing leading or critical role for distinguished organizations",
        "evidence_types": ["org_charts", "role_descriptions", "impact_evidence"],
    },
    9: {
        "name": "High Salary",
        "description": "Evidence of commanding a high salary or remuneration",
        "evidence_types": ["salary_documentation", "industry_comparisons", "compensation_data"],
    },
    10: {
        "name": "Commercial Success",
        "description": "Evidence of commercial successes in the performing arts",
        "evidence_types": ["sales_data", "box_office", "streaming_metrics"],
    },
}


# Query templates for common graph operations
QUERY_TEMPLATES = {
    "find_person_publications": """
        MATCH (p:Person {id: $person_id})-[:AUTHORED]->(pub:Publication)
        RETURN pub
        ORDER BY pub.year DESC
    """,
    "find_criterion_evidence": """
        MATCH (e)-[:EVIDENCE_FOR]->(c:Criterion {number: $criterion_number})
        RETURN e
    """,
    "find_person_criteria": """
        MATCH (p:Person {id: $person_id})-[:MEETS_CRITERION]->(c:Criterion)
        RETURN c, COUNT(DISTINCT e) as evidence_count
    """,
    "find_citation_network": """
        MATCH (pub:Publication {id: $publication_id})<-[:CITED_BY]-(citing:Publication)
        RETURN citing
        ORDER BY citing.year DESC
    """,
    "find_collaborators": """
        MATCH (p1:Person {id: $person_id})-[:AUTHORED]->(pub:Publication)<-[:AUTHORED]-(p2:Person)
        WHERE p1 <> p2
        RETURN DISTINCT p2, COUNT(pub) as collaboration_count
        ORDER BY collaboration_count DESC
    """,
    "evaluate_case_strength": """
        MATCH (case:Case {id: $case_id})-[r:MEETS_CRITERION]->(c:Criterion)
        OPTIONAL MATCH (e)-[:EVIDENCE_FOR]->(c)
        RETURN c.number, c.name, r.strength, COUNT(DISTINCT e) as evidence_count
        ORDER BY c.number
    """,
}


def create_default_schema() -> KnowledgeGraphSchema:
    """Create and return the default knowledge graph schema."""
    return KnowledgeGraphSchema()


def get_eb1a_criteria() -> dict[int, dict[str, Any]]:
    """Get EB-1A criteria definitions."""
    return EB1A_CRITERIA.copy()


def get_query_template(name: str) -> str | None:
    """Get a query template by name."""
    return QUERY_TEMPLATES.get(name)


__all__ = [
    # Constants
    "EB1A_CRITERIA",
    "QUERY_TEMPLATES",
    "Entity",
    "EntitySchema",
    # Enums
    "EntityType",
    # Schema class
    "KnowledgeGraphSchema",
    # Data classes
    "PropertySchema",
    "RelationType",
    "Relationship",
    "RelationshipSchema",
    # Functions
    "create_default_schema",
    "get_eb1a_criteria",
    "get_query_template",
]
