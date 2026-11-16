<?php declare(strict_types=1);
/*
 * (c) shopware AG <info@shopware.com>
 * For the full copyright and license information, please view the LICENSE
 * file that was distributed with this source code.
 */

namespace Swag\MigrationMagento\Profile\Magento\DataSelection\DataSet;

use Shopware\Core\Framework\Log\Package;
use Swag\MigrationMagento\Profile\Magento\MagentoProfileInterface;
use SwagMigrationAssistant\Migration\DataSelection\DataSet\DataSet;
use SwagMigrationAssistant\Migration\DataSelection\DefaultEntities;
use SwagMigrationAssistant\Migration\MigrationContextInterface;

/**
 * Skeleton DataSet. Declares one migratable entity type to the Migration Assistant.
 * Place in src/Profile/Magento/DataSelection/DataSet/. Register in magento.xml with
 * the tag: shopware.migration.data_set. Add it to a DataSelection in dependency order.
 */
#[Package('fundamentals@after-sales')]
class MyEntityDataSet extends DataSet
{
    public static function getEntity(): string
    {
        // The entity key threaded through Reader, Converter and the mapping table.
        // Reuse a DefaultEntities::* constant when the target is a known Shopware entity.
        return DefaultEntities::MY_ENTITY; // e.g. 'my_entity'
    }

    public function supports(MigrationContextInterface $migrationContext): bool
    {
        return $migrationContext->getProfile() instanceof MagentoProfileInterface;
    }
}
