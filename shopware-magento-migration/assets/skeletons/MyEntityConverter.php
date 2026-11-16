<?php declare(strict_types=1);
/*
 * (c) shopware AG <info@shopware.com>
 * For the full copyright and license information, please view the LICENSE
 * file that was distributed with this source code.
 */

namespace Swag\MigrationMagento\Profile\Magento\Converter;

use Shopware\Core\Framework\Context;
use Shopware\Core\Framework\Log\Package;
use SwagMigrationAssistant\Migration\Converter\ConvertStruct;
use SwagMigrationAssistant\Migration\DataSelection\DefaultEntities;
use SwagMigrationAssistant\Migration\MigrationContextInterface;

/**
 * Skeleton converter (the all-versions base — put the real logic here, once).
 * Place in src/Profile/Magento/Converter/; this base serves Magento 1.9 and every 2.x version.
 * Only if some behaviour must differ across all of 2.x vs 1.9, add an intermediate subclass in
 * src/Profile/Magento2/Converter/ that extends this base (as ProductConverter <- Magento2ProductConverter
 * does). Then create a thin per-version subclass (see MyEntityConverter.version.php.txt) and register
 * them in DI with the tag shopware.migration.converter, each subclass using parent="<base class id>".
 *
 * Contract: convert one raw Magento row into a Shopware payload, resolving every id
 * through the MappingService. Never write shop entities here.
 */
#[Package('fundamentals@after-sales')]
abstract class MyEntityConverter extends MagentoConverter
{
    protected string $connectionId;

    protected Context $context;

    public function getSourceIdentifier(array $data): string
    {
        return (string) $data['entity_id']; // the Magento primary key for this entity
    }

    public function convert(array $data, Context $context, MigrationContextInterface $migrationContext): ConvertStruct
    {
        $this->generateChecksum($data);
        $this->context = $context;
        $this->connectionId = $migrationContext->getConnection()->getId();

        // 1. Resolve (or create) the Shopware UUID for THIS record.
        $this->mainMapping = $this->mappingService->getOrCreateMapping(
            $this->connectionId,
            DefaultEntities::MY_ENTITY,
            $data['entity_id'],
            $context,
            $this->checksum
        );

        $converted = [];
        $converted['id'] = $this->mainMapping['entityId'];

        // 2. Resolve a FOREIGN reference — and SKIP the record if its dependency
        //    wasn't migrated, instead of writing a dangling reference.
        //    (Prevents the cascade described in shopware/shopware#10649.)
        if (isset($data['parent_id'])) {
            $parentMapping = $this->mappingService->getMapping(
                $this->connectionId,
                DefaultEntities::SOME_PARENT,
                $data['parent_id'],
                $context
            );

            if ($parentMapping === null) {
                // Optionally log a missing-dependency entry via $this->loggingService.
                return new ConvertStruct(null, $data); // do NOT write a dangling record
            }

            $converted['parentId'] = $parentMapping['entityId'];
            unset($data['parent_id']);
        }

        // 3. Copy + type-cast fields. unset() each consumed source field so anything
        //    left over surfaces in the second ConvertStruct argument (nothing silently lost).
        unset($data['entity_id']);
        $this->convertValue($converted, 'name', $data, 'source_name', self::TYPE_STRING);

        $this->updateMainMapping($migrationContext, $context);

        $resultData = $data === [] ? null : $data;

        return new ConvertStruct($converted, $resultData, $this->mainMapping['id'] ?? null);
    }
}
