# CMS Publishing Safety Gate

Publishing is a two-step flow:

```text
Approved publish package
-> Publication preview dry run
-> Explicit publish gate
```

The default behavior is safe:

```text
ENABLE_REAL_PUBLISHING=false
CMS_PROVIDER=mock
CMS_DESTINATION_TYPE=generic_cms
```

## Preview

Preview prepares a destination payload without external side effects:

```text
POST /api/tasks/packages/{package_id}/publication-preview
GET  /api/tasks/packages/{package_id}/publication-previews
```

If the source task has an approved product content profile, the preview payload includes:

- `product_card_json`;
- schema.org `Product`;
- schema.org `Article` linked to the product through `mainEntity` and `about`.

Without an approved product profile, the payload stays article-only.

## Publish Gate

The publish endpoint is intentionally hard to call by accident:

```text
POST /api/tasks/publication-previews/{preview_id}/publish
```

Payload:

```json
{
  "confirmation_phrase": "publish:{preview_id}"
}
```

The service publishes only when all checks pass:

- preview status is `dry_run_ready`;
- `ENABLE_REAL_PUBLISHING=true`;
- active CMS provider matches the provider that created the preview;
- confirmation phrase exactly equals `publish:{preview_id}`.

The current adapter is still `mock-cms`, so tests can validate the publish path without touching a real CMS.

## Next Real CMS Work

Before connecting a real destination:

- choose the target CMS;
- add a destination-specific adapter;
- map product-card fields to CMS fields;
- require staging-domain smoke tests;
- log every real publish result and external URL.
