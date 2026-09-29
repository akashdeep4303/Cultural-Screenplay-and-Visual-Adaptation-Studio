Project 6c54ea3d
Culture: majhi / rural / script=roman

## Canonical characters
- CHAR_MOTHER: Mother → Surjit Kaur aliases=['Mother', 'Bebe', 'Bebe Surjit']
- CHAR_ADAM: Adam → Jaswant Singh aliases=['Adam', 'Jassi', 'Jaswant']
- CHAR_UNCLE: Uncle → Mama Jagtar Singh aliases=['Uncle', 'Mama', 'Jagtar']
- CHAR_SISTER: Sister → Simran Kaur aliases=['Sister', 'Simran', 'Kudi']
- CHAR_FRIEND: Friend → Harpreet Singh aliases=['Friend', 'Happy', 'Harpreet']

## Costumes (one variant unless story changes them)
- COST_MOTHER_01 for CHAR_MOTHER scenes=['SC01', 'SC02', 'SC04']
- COST_ADAM_01 for CHAR_ADAM scenes=['SC01', 'SC02', 'SC03', 'SC04']
- COST_UNCLE_01 for CHAR_UNCLE scenes=['SC01']
- COST_SISTER_01 for CHAR_SISTER scenes=['SC01', 'SC02', 'SC04']
- COST_FRIEND_01 for CHAR_FRIEND scenes=['SC02', 'SC03']

## Prop / knowledge / costume state
### SC01
wearing={'CHAR_MOTHER': 'COST_MOTHER_01', 'CHAR_ADAM': 'COST_ADAM_01', 'CHAR_UNCLE': 'COST_UNCLE_01', 'CHAR_SISTER': 'COST_SISTER_01'}
carrying={'CHAR_ADAM': ['PROP_LETTER']}
knowledge={'CHAR_SISTER': ['letter_exists'], 'CHAR_MOTHER': ['suspects_family_matter']}
emotion={'CHAR_ADAM': 'avoidance', 'CHAR_MOTHER': 'worry'}
- Adam conceals the unopened letter in his jacket.
### SC02
wearing={'CHAR_FRIEND': 'COST_FRIEND_01', 'CHAR_ADAM': 'COST_ADAM_01', 'CHAR_SISTER': 'COST_SISTER_01', 'CHAR_MOTHER': 'COST_MOTHER_01'}
carrying={'CHAR_ADAM': ['PROP_LETTER']}
knowledge={'CHAR_SISTER': ['letter_exists', 'lie_about_course'], 'CHAR_MOTHER': ['suspects_family_matter'], 'CHAR_FRIEND': ['uncle_wants_shop']}
emotion={'CHAR_ADAM': 'cornered', 'CHAR_MOTHER': 'insists_on_truth'}
- Letter remains in Adam's pocket; it does not change hands.
### SC03
wearing={'CHAR_FRIEND': 'COST_FRIEND_01', 'CHAR_ADAM': 'COST_ADAM_01'}
carrying={'CHAR_ADAM': ['PROP_LETTER']}
knowledge={'CHAR_SISTER': ['letter_exists', 'lie_about_course'], 'CHAR_MOTHER': ['suspects_family_matter'], 'CHAR_FRIEND': ['uncle_wants_shop']}
emotion={'CHAR_ADAM': 'public_pressure', 'CHAR_FRIEND': 'pushes_him_home'}
- Letter remains in Adam's pocket; it does not change hands.
### SC04
wearing={'CHAR_ADAM': 'COST_ADAM_01', 'CHAR_MOTHER': 'COST_MOTHER_01', 'CHAR_SISTER': 'COST_SISTER_01'}
carrying={}
knowledge={'CHAR_SISTER': ['letter_exists', 'lie_about_course'], 'CHAR_MOTHER': ['knows_shop_offer', 'suspects_family_matter'], 'CHAR_FRIEND': ['uncle_wants_shop']}
emotion={'CHAR_ADAM': 'admission', 'CHAR_MOTHER': 'dignity_restored', 'CHAR_SISTER': 'solidarity'}
- Letter transfers from Adam's pocket to the baithak table — household custody.

## Contradictions
None. Letter custody, costumes, and knowledge track across scenes.

## Generation gates
extraction_approved=True
plan_approved=True
costumes_approved=True