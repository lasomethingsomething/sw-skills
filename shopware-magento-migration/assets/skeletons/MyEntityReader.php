<?php declare(strict_types=1);
/*
 * (c) shopware AG <info@shopware.com>
 * For the full copyright and license information, please view the LICENSE
 * file that was distributed with this source code.
 */

namespace Swag\MigrationMagento\Profile\Magento\Gateway\Local\Reader;

use Shopware\Core\Framework\Log\Package;
use SwagMigrationAssistant\Migration\MigrationContextInterface;
use SwagMigrationAssistant\Migration\TotalStruct;

/**
 * Skeleton reader (SHARED base). Pulls raw rows out of the Magento database.
 * Place in src/Profile/Magento/Gateway/Local/Reader/. Create a per-version concrete
 * reader (Magento2X\Gateway\Local\Reader\Magento2XMyEntityReader) holding the version
 * SQL, register it in each magentoXX.xml with the tag shopware.migration.reader and
 * parent="<this class id>", passing the ConnectionFactory service as an argument.
 *
 * AbstractReader gives you a configured Doctrine connection ($this->getConnection(...))
 * via the ConnectionFactory; see existing readers (CustomerReader, CategoryReader) for
 * the exact helpers available in your plugin version.
 */
#[Package('fundamentals@after-sales')]
abstract class MyEntityReader extends AbstractReader
{
    public function read(MigrationContextInterface $migrationContext, array $params = []): array
    {
        $connection = $this->getConnection($migrationContext);

        $limit = $migrationContext->getLimit();
        $offset = $migrationContext->getOffset();

        // Build the SQL for your entity. For attribute-heavy (EAV) entities you will
        // join *_entity against *_entity_{varchar,int,decimal,...} on attribute ids.
        //
        // PERFORMANCE: naive LIMIT/OFFSET pagination degrades badly at high offsets on
        // large tables (shopware/shopware#10645, #10642). Prefer keyset/cursor pagination
        // (WHERE id > :lastId ORDER BY id LIMIT :limit) for big entities where feasible.
        $query = $connection->createQueryBuilder();
        $query->select('*')
            ->from($this->tablePrefix . 'my_entity')
            ->setFirstResult($offset)
            ->setMaxResults($limit);

        $rows = $query->executeQuery()->fetchAllAssociative();

        // Optionally enrich rows here (fetch related EAV attributes / relations and
        // merge them in) before returning. Return a list of associative arrays — each
        // element is one record handed to the Converter.
        return $rows;
    }

    public function readTotal(MigrationContextInterface $migrationContext): ?TotalStruct
    {
        $connection = $this->getConnection($migrationContext);

        $total = (int) $connection->createQueryBuilder()
            ->select('COUNT(*)')
            ->from($this->tablePrefix . 'my_entity')
            ->executeQuery()
            ->fetchOne();

        return new TotalStruct(MyEntityDataSet::getEntity(), $total);
    }
}
